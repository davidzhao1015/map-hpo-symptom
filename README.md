# **Standardizing Clinical Symptom Terms with HPO in Python**

Summary: A lightweight, reproducible pipeline that maps free-text symptoms to Human Phenotype Ontology (HPO) terms with verification and context, producing a clean, structured table for evidence synthesis and modeling.

**Why this matters**

In rare-disease research, symptoms are often reported in free text. That makes cross-study comparisons, systematic reviews, and meta-analyses error-prone and time-intensive. By standardizing to HPO IDs and hierarchy, we unlock consistent, machine-readable clinical features for downstream use (registries, epidemiology models, ML).

**What I built**

A modular Python workflow that:

- Queries the JAX HPO API for candidate terms
- Scores text similarity (RapidFuzz-first)
- Checks official HPO synonyms & definitions from the ontology
- Extracts the lineage path to root for context
- Applies a clear accept/reject rule and returns a tidy, 8-field record per symptom

**Inputs → Outputs (at a glance)**

- Input: one or more reported symptoms (strings)
- Output: table with
reported_symptom, hpo_term, hpo_id, definition, rank, path, fuzzy_score, status


