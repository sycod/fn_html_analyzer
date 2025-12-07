.PHONY: help install clean analyze analyze-gui visualize lint format test

# Variables
PYTHON := python3
PIP := pip3
VENV := venv
URLS_FILE ?= ./urls_example.txt
OUTPUT_DIR ?= ./analyse_results

# Couleurs pour l'affichage
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Affiche cette aide
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║     Facta Nova - Web Semantic Analysis Toolkit             ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Usage:$(NC)"
	@echo "  make $(GREEN)help$(NC)                 Affiche cette aide"
	@echo "  make $(GREEN)install$(NC)              Installe les dépendances"
	@echo "  make $(GREEN)analyze$(NC)              Lance l'analyse complète (usage: make analyze URLS_FILE=urls.txt OUTPUT_DIR=./results)"
	@echo "  make $(GREEN)analyze-gui$(NC)          Ouvre le notebook Jupyter"
	@echo "  make $(GREEN)visualize$(NC)            Génère toutes les visualisations"
	@echo "  make $(GREEN)clean$(NC)                Nettoie les fichiers temporaires"
	@echo "  make $(GREEN)clean-all$(NC)            Nettoie tout (résultats + temp)"
	@echo "  make $(GREEN)lint$(NC)                 Vérifie la qualité du code"
	@echo "  make $(GREEN)format$(NC)               Formate le code"
	@echo "  make $(GREEN)test$(NC)                 Lance les tests"
	@echo ""
	@echo "$(YELLOW)Exemples:$(NC)"
	@echo "  make analyze URLS_FILE=./urls.txt OUTPUT_DIR=./results"
	@echo "  make analyze-gui"
	@echo ""

install: ## Installe les dépendances Python
	@echo "$(BLUE)📦 Installation des dépendances...$(NC)"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Dépendances installées$(NC)"

analyze: ## Lance l'analyse complète
	@echo "$(BLUE)🔍 Lancement de l'analyse...$(NC)"
	@echo "$(YELLOW)  URLs: $(URLS_FILE)$(NC)"
	@echo "$(YELLOW)  Output: $(OUTPUT_DIR)$(NC)"
	$(PYTHON) ./src/batch_analyse.py -l $(URLS_FILE) -o $(OUTPUT_DIR) -v
	@echo "$(GREEN)✓ Analyse terminée$(NC)"
	@echo "$(BLUE)📊 Résultats dans: $(OUTPUT_DIR)$(NC)"

analyze-quick: ## Lance l'analyse sans conservar les fichiers temporaires
	@echo "$(BLUE)⚡ Analyse rapide (sans fichiers temporaires)...$(NC)"
	$(PYTHON) ./src/batch_analyse.py -l $(URLS_FILE) -o $(OUTPUT_DIR)
	@echo "$(GREEN)✓ Analyse terminée$(NC)"

analyze-keep-temp: ## Lance l'analyse en conservant les HTML nettoyés
	@echo "$(BLUE)🔍 Analyse avec conservation des HTML...$(NC)"
	$(PYTHON) ./src/batch_analyse.py -l $(URLS_FILE) -o $(OUTPUT_DIR) --keep-temp -v
	@echo "$(GREEN)✓ HTML conservés dans: ./temp_cleaned_html$(NC)"

analyze-gui: ## Ouvre le notebook Jupyter pour explorer les résultats
	@echo "$(BLUE)📓 Lancement du notebook Jupyter...$(NC)"
	jupyter notebook analyse_visualisation.ipynb

visualize: ## Génère les visualisations seulement (nécessite un CSV existant)
	@echo "$(BLUE)📊 Génération des visualisations...$(NC)"
	$(PYTHON) -c "import pandas as pd; exec(open('scripts/visualize_only.py').read())"
	@echo "$(GREEN)✓ Visualisations générées$(NC)"

clean: ## Nettoie les fichiers temporaires
	@echo "$(YELLOW)🧹 Nettoyage des fichiers temporaires...$(NC)"
	rm -rf temp_cleaned_html/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Fichiers temporaires supprimés$(NC)"

clean-all: clean ## Nettoie tout (résultats + temporaires)
	@echo "$(RED)🗑️  Suppression de tous les résultats...$(NC)"
	rm -rf analyse_results/
	rm -rf analyse_globale.csv
	rm -rf analyse.csv
	@echo "$(GREEN)✓ Tous les résultats supprimés$(NC)"

lint: ## Vérifie la qualité du code Python
	@echo "$(BLUE)🔍 Vérification du code...$(NC)"
	$(PYTHON) -m py_compile src/analyse_structure_html.py src/batch_analyse.py src/scrap_clean/clean_html.py
	@echo "$(GREEN)✓ Syntaxe correcte$(NC)"

format: ## Formate le code avec black (si disponible)
	@echo "$(BLUE)✏️  Formatage du code...$(NC)"
	$(PYTHON) -m pip install black 2>/dev/null || true
	black src/*.py src/scrap_clean/*.py 2>/dev/null || echo "$(YELLOW)Black non disponible, installation ignorée$(NC)"
	@echo "$(GREEN)✓ Code formaté$(NC)"

test: ## Lance les tests unitaires
	@echo "$(BLUE)🧪 Lancement des tests...$(NC)"
	@if [ -f "tests/test_analyse.py" ]; then \
		$(PYTHON) -m pytest tests/ -v; \
	else \
		echo "$(YELLOW)⚠️  Aucun test trouvé dans tests/$(NC)"; \
	fi

info: ## Affiche des informations sur l'environnement
	@echo "$(BLUE)ℹ️  Informations de l'environnement:$(NC)"
	@echo "$(YELLOW)Python:$(NC) $$($(PYTHON) --version)"
	@echo "$(YELLOW)Pip:$(NC) $$($(PIP) --version)"
	@echo "$(YELLOW)Répertoire courant:$(NC) $$(pwd)"
	@echo "$(YELLOW)Fichiers de configuration:$(NC)"
	@ls -1 requirements.txt 2>/dev/null && echo "  ✓ requirements.txt" || echo "  ✗ requirements.txt manquant"
	@ls -1 Makefile 2>/dev/null && echo "  ✓ Makefile" || echo "  ✗ Makefile manquant"

status: ## Affiche le statut du projet
	@echo "$(BLUE)📊 Statut du projet:$(NC)"
	@echo ""
	@echo "$(YELLOW)Dépendances:$(NC)"
	@if [ -f "requirements.txt" ]; then \
		echo "  $(GREEN)✓$(NC) requirements.txt trouvé"; \
	else \
		echo "  $(RED)✗$(NC) requirements.txt manquant"; \
	fi
	@echo ""
	@echo "$(YELLOW)Résultats existants:$(NC)"
	@if [ -d "analyse_results" ]; then \
		echo "  $(GREEN)✓$(NC) analyse_results/"; \
	fi
	@if [ -f "analyse.csv" ]; then \
		echo "  $(GREEN)✓$(NC) analyse.csv"; \
	fi
	@echo ""
	@echo "$(YELLOW)Scripts disponibles:$(NC)"
	@ls -1 src/*.py src/scrap_clean/*.py 2>/dev/null | sed 's/^/  ✓ /'
	@echo ""

# Recettes invisibles (pas affichées dans help)
.SILENT: help info status
.PHONY: help install clean analyze analyze-quick analyze-keep-temp analyze-gui visualize lint format test info status

# Cible par défaut
.DEFAULT_GOAL := help
