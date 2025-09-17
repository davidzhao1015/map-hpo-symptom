#===============================================================================================
#
# A collection of functions to standardize free-text clinical symptoms using HPO terms and IDs
#
#===============================================================================================


#--------------------------------------
# Necessary imports
#--------------------------------------

import requests
from fuzzywuzzy import process
import pandas as pd
import obonet
from functools import lru_cache





#--------------------------------------
# Map reported terms to HPO terms
#--------------------------------------
import requests

# --- Step 1: Map reported symptoms to HPO terms using the HPA API -----------------
# Note: The HPA API is not always reliable. If the API fails,
# consider using a local database or a different API.

def map_symptoms_to_hpo(symptom):
    """
    Map reported symptoms to HPO terms using the HPA API.
    """
    url = f"https://ontology.jax.org/api/hp/search/?q={symptom}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # raises HTTPError if not 200 OK
        json_data = response.json()
        results = json_data.get('terms', [])
        if results:
            top = results[0]  # Take top result
            return (top["name"], top["id"])  # return matched term and HPO ID as a tuple
        else:
            return (None, None)
    except requests.exceptions.RequestException as e:
        # print(f"Request failed for term '{symptom}': {e}")
        return (None, None)
    except ValueError as ve:
        # print(f"Invalid JSON for term '{symptom}': {ve}")
        return (None, None)


#-------------------------------------------------------------------------------------------------
# Algorithm to verify HPO terms
# 1. Calculate the fuzzy or cosine similarity score between the input term and the matched term
# 2. If the score is above a certain threshold (e.g., 0.8), consider it a match.
# 3. If the score is below the threshold, check if the matched term is a synonym of the input term.
# 4. If it is, consider it a match.
# 5. If not, return None or a message indicating no match was found.
#-------------------------------------------------------------------------------------------------

from fuzzywuzzy import process
import pandas as pd

# --- Step 2: Standardize clinical terms using fuzzy matching -----------------
# Note: This function requires the `spacy` library and the `en_core_web_md` model.
def estimate_fuzzy_score(input_term, hpo_term):
    """
    Estimate the fuzzy score between the input term and the HPO term.

    Parameters:
    input_term: str
        The term reported in the study.
    hpo_term: str
        The term from the HPO database.
    Returns:
    fuzzy_score: float
        The fuzzy score between the input term and the HPO term.

    """
    if not isinstance(input_term, str):
        raise ValueError("reported_term must be a string.")
    
    best_match_fuzzy, fuzzy_score = process.extractOne(input_term, [hpo_term])
    return fuzzy_score


# --- Step 3: Look up HPO synonyms and definition -----------------
import obonet
def get_hpo_definitions_and_synonyms(hpo_id):
    """
    Get the definition and synonyms for a given HPO term ID.
    """
    url = 'http://purl.obolibrary.org/obo/hp.obo' # URL points to the Human Phenotype Ontology (HPO) in OBO format, hosted by the OBO Foundry
    graph = obonet.read_obo(url)

    if hpo_id in graph.nodes:
        synonyms = graph.nodes[hpo_id].get('synonyms', [])
        definition = graph.nodes[hpo_id].get('def', 'NA')
        return synonyms, definition
    else:
        return None, None
    


# --- Step 4: Get full lineage for a given HPO ID -----------------
import obonet
from functools import lru_cache

HPO_URL = "http://purl.obolibrary.org/obo/hp.obo"

# Cache the graph so it loads only once
@lru_cache(maxsize=1)
def load_graph():
    return obonet.read_obo(HPO_URL)

def get_rank_and_path(hpo_id):
    """
    Return rank and path from root to this term (shortest path).
    """
    graph = load_graph()
    if hpo_id not in graph:
        return None, []

    path = [hpo_id]
    depth = 0
    current = hpo_id
    while True:
        parents = graph.nodes[current].get("is_a", [])
        if not parents:
            break
        current = parents[0]  # take first parent if multiple
        path.append(current)
        depth += 1
        if current == "HP:0000001":
            break
    return depth, list(reversed(path)) 



# --- Pipeline function to chain step 1-3 -----------------
def map_symptoms_to_hpo_pipeline(symptom):
    """
    Map reported symptoms to HPO terms and get synonyms and definitions.

    Parameters:
    symptom: str
        The term reported in the study.

    Returns:
    hpo_term: str or None
        The term from the HPO database.
    hpo_id: str or None
        The ID of the term from the HPO database.
    fuzzy_score: float
        The fuzzy score between the input term and the HPO term (0 if no match).
    definition: str or None
        The definition of the HPO term.
    rank: int or None
        The rank (depth) of the HPO term in the ontology.
    path: list of str
        The list of HPO IDs representing the path from the root to this term.
    status: str
        The status of the mapping ('matched' or 'not matched').
    """
    # Step 1: Map reported symptoms to HPO terms
    hpo_term, hpo_id = map_symptoms_to_hpo(symptom)

    # If no match found, return immediately
    if hpo_term is None or hpo_id is None:
        return symptom, None, None, 0, 'not matched'

    # Step 2: Estimate fuzzy score
    fuzzy_score = estimate_fuzzy_score(symptom, hpo_term)

    # Step 3: Get HPO definitions and synonyms
    synonyms, definition = get_hpo_definitions_and_synonyms(hpo_id)
    
    # Step 4: Get full lineage
    rank, path = get_rank_and_path(hpo_id)
    # print(f"Rank: {rank}, Path: {path}")

    # Step 5: Check if match is acceptable
    if fuzzy_score >= 80 or (hpo_term.lower() in [s.lower() for s in synonyms]):
        return symptom, hpo_term, hpo_id, definition, rank, path, fuzzy_score, 'matched'
    else:
        return symptom, hpo_term, hpo_id, definition, rank, path, fuzzy_score, 'not matched'



# Test case
# test_symptoms = [
#     "limitation of (OD or OS or OU) adduction",  # likely unmatched
#     "ptosis",  # expected to match
#     "muscle weakness"
# ]

# for s in test_symptoms:
#     print(f"Symptom: {s}")
#     print(map_symptoms_to_hpo_pipeline(s))
#     print("------")






# --- Helper: Look up HPO ID based on HPO terms ---------------------

import obonet

def get_hpo_id_from_term(hpo_term):
    """
    Get the HPO ID for a given HPO term.
    """
    url = 'http://purl.obolibrary.org/obo/hp.obo' # URL points to the Human Phenotype Ontology (HPO) in OBO format, hosted by the OBO Foundry
    graph = obonet.read_obo(url)

    for node_id, data in graph.nodes(data=True):
        if data.get('name', '').lower() == hpo_term.lower():
            return node_id
    return None

# Test case
# print(get_hpo_id_from_term('ptosis'))
# print(get_hpo_id_from_term('drooping eyelids'))
# print(get_hpo_id_from_term('waddling gait'))
# print(get_hpo_id_from_term('facial weakness'))




# --- Helper: Get HPO terms from ID -------------------------

import obonet

def get_hpo_term_from_id(hpo_id):
    """
    Get the HPO term (name) for a given HPO ID.
    
    Parameters:
        hpo_id (str): HPO ID (e.g., "HP:0000486")
    
    Returns:
        str: HPO term name or None if ID not found
    """
    url = 'http://purl.obolibrary.org/obo/hp.obo'
    graph = obonet.read_obo(url)

    # Check if the ID exists in the graph
    if hpo_id in graph.nodes:
        return graph.nodes[hpo_id].get('name', None)
    else:
        return None
    
# Test case
hpo_id = "HP:0025142"
hpo_term = get_hpo_term_from_id(hpo_id)
print(f"HPO ID: {hpo_id} -> HPO Term: {hpo_term}")
