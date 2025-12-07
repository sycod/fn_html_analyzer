# Analyse sémantique Web

## Prérequis
- Python 3 et `pip`
- `make` installé (macOS/Linux : déjà présent ou via package manager)

## Installation
```bash
make install
```

## Lancer une analyse complète
```bash
make analyze URLS_FILE=./urls_example.txt OUTPUT_DIR=./analyse_results
```
- Télécharge, nettoie et analyse les pages
- Génère :
  - `analyse_complete.csv` : données détaillées par page
  - `analyse_globale.csv` : top 50 mots-clés agrégés
  - `phrases_globales.csv` : **top 50 phrases phares agrégées** (nouveau)
  - dossier `visualisations/` : graphiques d'analyse
  - `rapport_analyse.pdf` : rapport complet avec phrases phares
  - `log.txt` : récapitulatif de l'analyse

### Variantes utiles
- Rapide (sans verbeux) :
  ```bash
  make analyze-quick URLS_FILE=./urls_example.txt OUTPUT_DIR=./analyse_results
  ```
- Conserver les HTML nettoyés :
  ```bash
  make analyze-keep-temp URLS_FILE=./urls_example.txt OUTPUT_DIR=./analyse_results
  ```
- Désactiver le PDF :
  ```bash
  python src/batch_analyse.py -l ./urls_example.txt -o ./analyse_results --no-pdf
  ```

## Nouvelles fonctionnalités

### Agrégation globale des phrases phares
L'outil génère maintenant automatiquement une **analyse des principales phrases au niveau global** :

1. **Fichier `phrases_globales.csv`** : 
   - Liste les 50 phrases les plus pertinentes dans tous les documents analysés
   - Inclut : rang, phrase, fréquence d'apparition, longueur et score de pertinence
   - Score basé sur : **fréquence × (longueur / longueur_max)** — favorise les phrases longues et fréquentes, normalisées par la plus longue phrase trouvée

2. **Visualisation `top_phrases_globales.png`** :
   - Graphique en barres horizontales des 15 phrases phares
   - Visualise le score de pertinence de chaque phrase

3. **Rapport PDF enrichi** :
   - Nouvelle section "Top 30 Phrases Phares" dans le rapport PDF
   - Tableau avec rang, phrase, fréquence et score

### Exemple d'utilisation
```python
from batch_analyse import aggregate_phrases

# Agréger les phrases phares à partir des données analysées
global_phrases = aggregate_phrases(all_data, top_n=50)

# Résultat: [(phrase, fréquence, longueur, score), ...]
for phrase, freq, length, score in global_phrases[:5]:
    print(f"{phrase}: fréquence={freq}, longueur={length} mots, score={score:.2f}")
```

## Nettoyage
```bash
make clean       # fichiers temporaires
make clean-all   # résultats + temporaires
```

## Qualité du code
```bash
make lint        # vérification syntaxique
make format      # formatage (black si installé)
```
