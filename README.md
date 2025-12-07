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
- Génère : `analyse_complete.csv`, `analyse_globale.csv`, dossier `visualisations/`, `rapport_analyse.pdf`, `log.txt`

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
