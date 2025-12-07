#!/usr/bin/env python3
"""
batch_analyse.py
Lit un fichier d'URLs, télécharge et nettoie chaque page HTML, puis analyse le contenu
pour générer un dossier d'analyse complet avec CSV, agrégations et visualisations.

Usage:
  python3 batch_analyse.py --list urls.txt --output-dir ./analyse_results
  python3 batch_analyse.py --list urls.txt -o ./results --keep-temp --verbose

Options:
  --list / -l       : fichier texte avec une URL par ligne (commentaires # ignorés)
  --output-dir / -o : dossier de sortie pour l'analyse (défaut: ./analyse_results)
  --temp-dir / -t   : dossier temporaire pour les HTML nettoyés (défaut: ./temp_cleaned_html)
  --keep-temp       : conserver les fichiers HTML temporaires après analyse
  --no-pdf          : ne pas générer le rapport PDF
  --timeout         : timeout pour les requêtes HTTP en secondes (défaut: 10)
  --verbose / -v    : mode verbeux
"""

import os
import sys
import csv
import argparse
import logging
import subprocess
import shutil
import ast
from pathlib import Path
from collections import Counter
from datetime import datetime
from analyse_structure_html import analyze_html

# Import matplotlib pour les visualisations
try:
    import matplotlib
    matplotlib.use('Agg')  # Backend non-interactif
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib non disponible, visualisations désactivées")

# Import wordcloud
try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False
    logging.warning("wordcloud non disponible")

# Import networkx pour réseau sémantique
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logging.warning("networkx non disponible")

# Import pandas pour PDF
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Import reportlab pour PDF
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning("reportlab non disponible, pas de génération PDF")


def read_urls(file_path):
    """Lit un fichier texte contenant une URL par ligne."""
    urls = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                urls.append(line)
    return urls


def clean_html_from_url(url, output_path, timeout=10, verbose=False):
    """Appelle clean_html.py pour télécharger et nettoyer une URL."""
    script_path = Path(__file__).parent / "scrap_clean" / "clean_html.py"
    
    if not script_path.exists():
        raise FileNotFoundError(f"Script clean_html.py introuvable: {script_path}")
    
    cmd = [
        sys.executable,
        str(script_path),
        "--url", url,
        "--output", str(output_path),
        "--timeout", str(timeout)
    ]
    
    if verbose:
        cmd.append("--verbose")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        if verbose:
            logging.debug(f"clean_html.py output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Erreur lors du nettoyage de {url}: {e.stderr}")
        return False


def aggregate_keywords(all_data):
    """Agrège tous les mots-clés, n-grams et phrases phares de toutes les pages."""
    all_keywords = Counter()
    
    for data in all_data:
        # 1. Mots-clés dominants
        keywords_str = data.get('Mots-clés dominants', '')
        if keywords_str:
            keywords = [kw.strip() for kw in str(keywords_str).split('|') if kw.strip()]
            for kw in keywords:
                all_keywords[kw] += 1
        
        # 2. N-grams depuis Fréquences
        freq_str = data.get('Fréquences', '')
        if freq_str and freq_str != '{}':
            try:
                freq_dict = ast.literal_eval(str(freq_str))
                for ngram, count in freq_dict.items():
                    all_keywords[ngram] += count
            except (ValueError, SyntaxError):
                continue
        
        # 3. Mots des phrases phares
        phrases_str = data.get('Phrases phares', '')
        if phrases_str:
            phrases = [p.strip() for p in str(phrases_str).split('|') if p.strip()]
            for phrase in phrases:
                words = phrase.lower().split()
                for word in words:
                    word = word.strip('.,!?;:()\'"')
                    if len(word) > 2:
                        all_keywords[word] += 1
    
    return all_keywords


def save_aggregated_csv(aggregated, output_path, top_n=50):
    """Sauvegarde l'agrégation globale dans un CSV."""
    top_keywords = aggregated.most_common(top_n)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Rang', 'Mot-clé / N-gram', 'Occurrences'])
        for i, (keyword, count) in enumerate(top_keywords, 1):
            writer.writerow([i, keyword, count])
    
    logging.info(f"CSV d'agrégation sauvegardé: {output_path}")


def read_aggregated_csv(csv_path):
    """Lit le CSV d'agrégation globale."""
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def generate_visualizations(all_data, aggregated, output_dir):
    """Génère les visualisations et les sauvegarde."""
    if not MATPLOTLIB_AVAILABLE:
        logging.warning("Matplotlib non disponible, visualisations ignorées")
        return
    
    viz_dir = Path(output_dir) / "visualisations"
    viz_dir.mkdir(exist_ok=True)
    
    # 1. Top 20 global des mots-clés
    logging.info("Génération: Top 20 global des mots-clés...")
    top20 = aggregated.most_common(20)
    if top20:
        keywords, counts = zip(*top20)
        
        plt.figure(figsize=(14, 8))
        plt.barh(range(len(keywords)), counts, color='teal', edgecolor='black')
        plt.yticks(range(len(keywords)), keywords)
        plt.xlabel('Nombre d\'occurrences', fontsize=12)
        plt.ylabel('Mots-clés / N-grams', fontsize=12)
        plt.title('Top 20 des mots-clés et n-grams (agrégé sur toutes les pages)', 
                  fontsize=14, fontweight='bold')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig(viz_dir / 'top20_global.png', dpi=150, bbox_inches='tight')
        plt.close()
    
    # 2. Distribution du nombre de liens internes
    logging.info("Génération: Distribution des liens internes...")
    link_counts = []
    for data in all_data:
        liens = data.get('Liens internes', '')
        if liens:
            count = len([l for l in liens.split('|') if l.strip()])
            link_counts.append(count)
    
    if link_counts:
        plt.figure(figsize=(10, 6))
        plt.hist(link_counts, bins=20, color='coral', edgecolor='black')
        plt.xlabel('Nombre de liens internes', fontsize=12)
        plt.ylabel('Fréquence', fontsize=12)
        plt.title('Distribution du nombre de liens internes par page', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(viz_dir / 'distribution_liens.png', dpi=150, bbox_inches='tight')
        plt.close()
    
    # 3. Word Cloud
    if WORDCLOUD_AVAILABLE:
        logging.info("Génération: Word Cloud...")
        try:
            # Créer un dictionnaire pour WordCloud
            wc_freq = dict(aggregated.most_common(100))
            
            wordcloud = WordCloud(
                width=1600, 
                height=900,
                background_color='white',
                colormap='viridis',
                prefer_horizontal=0.7,
                relative_scaling=0.5,
                min_font_size=10,
                collocations=False
            ).generate_from_frequencies(wc_freq)
            
            plt.figure(figsize=(16, 9))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.tight_layout(pad=0)
            plt.savefig(viz_dir / 'wordcloud.png', dpi=150, bbox_inches='tight')
            plt.close()
        except Exception as e:
            logging.warning(f"Erreur lors de la génération du word cloud: {e}")
    
    # 4. Réseau sémantique (Co-occurrence)
    if NETWORKX_AVAILABLE:
        logging.info("Génération: Réseau sémantique...")
        try:
            # Créer le graphe à partir des co-occurrences
            top_keywords_list = [k for k, _ in aggregated.most_common(30)]
            graph = nx.Graph()
            
            # Ajouter les nœuds
            for kw in top_keywords_list:
                graph.add_node(kw)
            
            # Ajouter les arêtes basées sur les co-occurrences
            for data in all_data:
                # Combiner tous les mots-clés de cette page
                page_keywords = set()
                
                # From 'Mots-clés dominants'
                keywords_str = data.get('Mots-clés dominants', '')
                if keywords_str:
                    keywords = [kw.strip() for kw in str(keywords_str).split('|') if kw.strip()]
                    page_keywords.update(keywords)
                
                # From 'Fréquences'
                freq_str = data.get('Fréquences', '')
                if freq_str and freq_str != '{}':
                    try:
                        freq_dict = ast.literal_eval(str(freq_str))
                        page_keywords.update(freq_dict.keys())
                    except (ValueError, SyntaxError):
                        pass
                
                # Créer des connexions entre les mots-clés de cette page
                page_keywords_list = [kw for kw in page_keywords if kw in top_keywords_list]
                for i, kw1 in enumerate(page_keywords_list):
                    for kw2 in page_keywords_list[i+1:]:
                        if graph.has_edge(kw1, kw2):
                            graph[kw1][kw2]['weight'] += 1
                        else:
                            graph.add_edge(kw1, kw2, weight=1)
            
            # Générer la visualisation
            if graph.number_of_edges() > 0:
                plt.figure(figsize=(16, 12))
                
                # Layout du graphe
                pos = nx.spring_layout(graph, k=2, iterations=50, seed=42)
                
                # Taille des nœuds basée sur la fréquence
                node_sizes = [aggregated[node] * 50 for node in graph.nodes()]
                
                # Largeur des arêtes basée sur le poids
                edge_widths = [graph[u][v]['weight'] * 0.5 for u, v in graph.edges()]
                
                # Dessiner
                nx.draw_networkx_nodes(
                    graph, pos,
                    node_size=node_sizes,
                    node_color='lightblue',
                    edgecolors='navy',
                    linewidths=2,
                    alpha=0.8
                )
                
                nx.draw_networkx_edges(
                    graph, pos,
                    width=edge_widths,
                    alpha=0.5,
                    edge_color='gray'
                )
                
                nx.draw_networkx_labels(
                    graph, pos,
                    font_size=9,
                    font_weight='bold',
                    font_color='darkblue'
                )
                
                plt.title('Réseau sémantique - Co-occurrences des mots-clés', 
                         fontsize=14, fontweight='bold')
                plt.axis('off')
                plt.tight_layout()
                plt.savefig(viz_dir / 'reseau_semantique.png', dpi=150, bbox_inches='tight')
                plt.close()
        except Exception as e:
            logging.warning(f"Erreur lors de la génération du réseau sémantique: {e}")
    
    # 5. Heatmap : Mots-clés par page
    logging.info("Génération: Heatmap mots-clés/pages...")
    try:
        import pandas as pd
        
        # Créer une matrice : pages × top 20 mots-clés
        top20_keywords = [k for k, _ in aggregated.most_common(20)]
        
        data_matrix = []
        page_labels = []
        
        for i, data in enumerate(all_data):
            page_label = data.get('URL', f'Page {i+1}').split('/')[-1] or f'Page {i+1}'
            page_labels.append(page_label[:30])  # Limiter la longueur
            
            row = []
            page_keywords = set()
            
            # Compter les occurrences de chaque mot-clé dans cette page
            keywords_str = data.get('Mots-clés dominants', '')
            if keywords_str:
                keywords = [kw.strip() for kw in str(keywords_str).split('|') if kw.strip()]
                page_keywords.update(keywords)
            
            freq_str = data.get('Fréquences', '')
            if freq_str and freq_str != '{}':
                try:
                    freq_dict = ast.literal_eval(str(freq_str))
                    for kw, count in freq_dict.items():
                        if kw in top20_keywords:
                            page_keywords.add(kw)
                except (ValueError, SyntaxError):
                    pass
            
            for kw in top20_keywords:
                row.append(1 if kw in page_keywords else 0)
            
            data_matrix.append(row)
        
        df_heatmap = pd.DataFrame(data_matrix, columns=top20_keywords, index=page_labels)
        
        plt.figure(figsize=(14, max(8, len(all_data) * 0.4)))
        import seaborn as sns
        sns.heatmap(
            df_heatmap,
            cmap='YlOrRd',
            cbar_kws={'label': 'Présence'},
            linewidths=0.5,
            linecolor='gray'
        )
        plt.title('Présence des top 20 mots-clés par page', fontsize=14, fontweight='bold')
        plt.xlabel('Mots-clés', fontsize=12)
        plt.ylabel('Pages', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(viz_dir / 'heatmap_keywords_pages.png', dpi=150, bbox_inches='tight')
        plt.close()
    except Exception as e:
        logging.warning(f"Erreur lors de la génération de la heatmap: {e}")
    
    logging.info(f"Visualisations sauvegardées dans {viz_dir}")


def generate_pdf_report(all_data, aggregated, output_dir, data_global):
    """Génère un rapport PDF complet."""
    if not REPORTLAB_AVAILABLE:
        logging.warning("reportlab non disponible, génération PDF ignorée")
        return
    
    logging.info("Génération du rapport PDF...")
    
    pdf_path = Path(output_dir) / "rapport_analyse.pdf"
    
    try:
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2e75b6'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=14
        )
        
        content = []
        
        # ========== PAGE 1: INTRODUCTION ==========
        content.append(Paragraph("RAPPORT D'ANALYSE SÉMANTIQUE WEB", title_style))
        content.append(Spacer(1, 0.3*inch))
        
        date_str = datetime.now().strftime("%d %B %Y à %H:%M:%S")
        content.append(Paragraph(f"<i>Généré le {date_str}</i>", styles['Normal']))
        content.append(Spacer(1, 0.5*inch))
        
        intro_text = """
        Ce rapport présente une analyse complète de la structure sémantique et du contenu web des domaines étudiés.
        L'analyse inclut l'extraction de mots-clés dominants, la génération de n-grams, l'identification de liens internes,
        et une agrégation globale des thèmes majeurs identifiés.
        """
        content.append(Paragraph(intro_text, normal_style))
        content.append(Spacer(1, 0.3*inch))
        
        # Liste des URLs
        content.append(Paragraph("URLs et Domaines Étudiés", heading_style))
        
        urls = [d.get('URL', '') for d in all_data if d.get('URL') and not str(d.get('URL')).startswith('ERREUR')]
        unique_domains = set()
        url_data = [['#', 'Domaine', 'URL']]
        
        for i, url in enumerate(urls, 1):
            if url:
                from urllib.parse import urlparse
                parsed = urlparse(str(url))
                domain = parsed.netloc or 'N/A'
                unique_domains.add(domain)
                url_data.append([str(i), domain, str(url)[:60] + ('...' if len(str(url)) > 60 else '')])
        
        if len(url_data) > 1:
            url_table = Table(url_data, colWidths=[0.5*inch, 1.5*inch, 3*inch])
            url_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e75b6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f0f0')),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
            ]))
            content.append(url_table)
        
        content.append(Spacer(1, 0.3*inch))
        content.append(Paragraph(f"<b>Total:</b> {len(urls)} URL(s) analysée(s) - {len(unique_domains)} domaine(s)", 
                                styles['Normal']))
        
        content.append(PageBreak())
        
        # ========== PAGE: ANALYSE GLOBALE ==========
        content.append(Paragraph("Analyse Globale - Top 50 Mots-clés et N-grams", heading_style))
        content.append(Spacer(1, 0.2*inch))
        
        global_data = [['Rang', 'Mot-clé / N-gram', 'Occurrences']]
        for row in data_global[:50]:
            global_data.append([
                row['Rang'],
                str(row['Mot-clé / N-gram'])[:50],
                row['Occurrences']
            ])
        
        global_table = Table(global_data, colWidths=[0.7*inch, 3.5*inch, 1.3*inch])
        global_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e75b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f0f0')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
        ]))
        content.append(global_table)
        
        content.append(PageBreak())
        
        # ========== PAGES: VISUALISATIONS ==========
        viz_dir = Path(output_dir) / "visualisations"
        if viz_dir.exists():
            content.append(Paragraph("Visualisations", heading_style))
            content.append(Spacer(1, 0.2*inch))
            
            viz_files = [
                ('top20_global.png', 'Top 20 Mots-clés et N-grams'),
                ('wordcloud.png', 'Nuage de Mots (Word Cloud)'),
                ('reseau_semantique.png', 'Réseau Sémantique - Co-occurrences'),
                ('heatmap_keywords_pages.png', 'Présence des Mots-clés par Page'),
                ('distribution_liens.png', 'Distribution des Liens Internes'),
            ]
            
            for filename, title in viz_files:
                viz_path = viz_dir / filename
                if viz_path.exists():
                    content.append(Paragraph(title, styles['Heading3']))
                    try:
                        img = Image(str(viz_path), width=6.5*inch, height=4*inch)
                        content.append(img)
                        content.append(Spacer(1, 0.2*inch))
                        content.append(PageBreak())
                    except Exception as e:
                        logging.warning(f"Erreur lors de l'ajout de l'image {filename}: {e}")
        
        # ========== PAGE FINALE: CONCLUSION ==========
        content.append(Paragraph("Conclusion", heading_style))
        content.append(Spacer(1, 0.3*inch))
        
        top_keyword = data_global[0]['Mot-clé / N-gram'] if data_global else "N/A"
        top_count = data_global[0]['Occurrences'] if data_global else "N/A"
        
        conclusion_text = f"""
        <b>Résumé de l'analyse:</b><br/><br/>
        
        Cette analyse sémantique a examiné <b>{len(urls)} URL(s)</b> réparties sur <b>{len(unique_domains)} domaine(s)</b>.
        Au total, <b>{len(all_data)} page(s)</b> ont été analysées avec succès.<br/><br/>
        
        <b>Principaux enseignements:</b><br/>
        • Le terme le plus fréquent est <b>"{top_keyword}"</b> avec <b>{top_count} occurrences</b><br/>
        • Les analyses unitaires révèlent des structures HTML variées et des stratégies de contenu distinctes<br/>
        • L'agrégation globale identifie les thèmes centraux qui unissent les différentes pages<br/>
        • Les visualisations mettent en lumière les co-occurrences sémantiques clés<br/><br/>
        
        <b>Recommandations:</b><br/>
        • Examiner le réseau sémantique pour identifier les clusters thématiques<br/>
        • Analyser la heatmap pour évaluer la cohérence sémantique du site<br/>
        • Utiliser le word cloud pour visualiser l'identité thématique globale<br/><br/>
        
        <i>Ce rapport a été généré automatiquement le {datetime.now().strftime("%d %B %Y à %H:%M:%S")}
        par l'outil d'analyse sémantique.</i>
        """
        
        content.append(Paragraph(conclusion_text, normal_style))
        
        # Construire le PDF
        doc.build(content)
        logging.info(f"✓ Rapport PDF généré: {pdf_path}")
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération du PDF: {e}")


def process_urls(urls, temp_dir, output_dir, timeout=10, verbose=False, generate_pdf=True):
    """Traite chaque URL : télécharge, nettoie, analyse, et génère les outputs."""
    all_data = []
    
    # Créer les dossiers
    temp_path = Path(temp_dir)
    output_path = Path(output_dir)
    temp_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Traiter chaque URL
    for i, url in enumerate(urls, 1):
        logging.info(f"[{i}/{len(urls)}] Traitement de {url}")
        
        html_filename = f"page_{i:03d}.html"
        html_path = temp_path / html_filename
        
        try:
            # 1. Télécharger et nettoyer le HTML
            logging.info(f"  → Téléchargement et nettoyage...")
            success = clean_html_from_url(url, html_path, timeout=timeout, verbose=verbose)
            
            if not success or not html_path.exists():
                raise Exception("Échec du téléchargement/nettoyage")
            
            # 2. Analyser le HTML nettoyé
            logging.info(f"  → Analyse du contenu...")
            data = analyze_html(str(html_path), url=url)
            all_data.append(data)
            logging.info(f"  ✓ Succès")
            
        except Exception as e:
            logging.error(f"  ✗ Erreur: {e}")
            all_data.append({
                "URL": url,
                "Title": f"ERREUR: {str(e)}",
                "H1": "", "H2": "", "H3": "",
                "Meta description": "", "Ancres internes": "",
                "Mots-clés dominants": "", "N-grams": "",
                "Fréquences": "", "Liens internes": "",
                "Phrases phares": "", "Extrait de texte principal": ""
            })
    
    if not all_data:
        logging.warning("Aucune donnée à exporter")
        return
    
    # 3. Écrire le CSV complet
    csv_path = output_path / "analyse_complete.csv"
    fieldnames = [
        "URL", "Title", "H1", "H2", "H3", "Meta description",
        "Ancres internes", "Mots-clés dominants", "N-grams", "Fréquences",
        "Liens internes", "Phrases phares", "Extrait de texte principal"
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for data in all_data:
            writer.writerow(data)
    
    logging.info(f"CSV complet généré: {csv_path} ({len(all_data)} pages)")
    
    # 4. Agrégation globale
    logging.info("Agrégation des mots-clés globaux...")
    aggregated = aggregate_keywords(all_data)
    
    # 5. Écrire le CSV d'agrégation
    agg_csv_path = output_path / "analyse_globale.csv"
    save_aggregated_csv(aggregated, agg_csv_path, top_n=50)
    
    # 6. Générer les visualisations
    logging.info("Génération des visualisations...")
    generate_visualizations(all_data, aggregated, output_path)
    
    # 7. Générer le PDF si demandé
    if generate_pdf:
        data_global = read_aggregated_csv(agg_csv_path)
        generate_pdf_report(all_data, aggregated, output_path, data_global)
    
    # 8. Créer un fichier récapitulatif
    summary_path = output_path / "log.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"Analyse générée le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"=" * 60 + "\n\n")
        f.write(f"Nombre d'URLs analysées: {len(urls)}\n")
        f.write(f"Nombre de pages traitées avec succès: {len(all_data)}\n\n")
        f.write(f"Fichiers générés:\n")
        f.write(f"  - analyse_complete.csv   : Données complètes pour toutes les pages\n")
        f.write(f"  - analyse_globale.csv    : Top 50 des mots-clés agrégés\n")
        f.write(f"  - log.txt                : Ce fichier (récapitulatif de l'analyse)\n")
        if generate_pdf:
            f.write(f"  - rapport_analyse.pdf    : Rapport PDF complet\n")
        f.write(f"  - visualisations/        : Graphiques PNG\n")
        f.write(f"      • top20_global.png   : Graphique en barres des top 20\n")
        f.write(f"      • distribution_liens.png   : Histogramme de distribution des liens\n")
        f.write(f"      • wordcloud.png      : Nuage de mots\n")
        f.write(f"      • reseau_semantique.png   : Réseau de co-occurrences\n")
        f.write(f"      • heatmap_keywords_pages.png   : Présence des mots-clés par page\n")
    
    print(f"\n{'='*60}")
    print(f"✓ Analyse terminée avec succès!")
    print(f"{'='*60}")
    print(f"Dossier de sortie: {output_path}")
    print(f"  - {len(all_data)} pages analysées")
    print(f"  - {aggregated.most_common(1)[0][1] if aggregated else 0} occurrences du terme le plus fréquent")
    print(f"  - CSV et visualisations générés")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Lit des URLs, télécharge/nettoie le HTML, et génère un dossier d'analyse complet"
    )
    parser.add_argument('-l', '--list', required=True, help='Fichier texte avec les URLs (une par ligne)')
    parser.add_argument('-o', '--output-dir', default='./analyse_results', 
                        help='Dossier de sortie pour l\'analyse (défaut: ./analyse_results)')
    parser.add_argument('-t', '--temp-dir', default='./temp_cleaned_html', 
                        help='Dossier temporaire pour les HTML nettoyés')
    parser.add_argument('--keep-temp', action='store_true', 
                        help='Conserver les fichiers HTML temporaires')
    parser.add_argument('--no-pdf', action='store_true',
                        help='Ne pas générer le rapport PDF')
    parser.add_argument('--timeout', type=int, default=10, 
                        help='Timeout HTTP en secondes (défaut: 10)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    
    # Lire les URLs
    if not os.path.exists(args.list):
        logging.error(f"Fichier d'URLs introuvable: {args.list}")
        sys.exit(1)
    
    urls = read_urls(args.list)
    if not urls:
        logging.error(f"Aucune URL trouvée dans {args.list}")
        sys.exit(1)
    
    logging.info(f"{len(urls)} URL(s) à traiter")
    
    # Traiter toutes les URLs
    try:
        process_urls(
            urls=urls,
            temp_dir=args.temp_dir,
            output_dir=args.output_dir,
            timeout=args.timeout,
            verbose=args.verbose,
            generate_pdf=not args.no_pdf
        )
    finally:
        # Nettoyer les fichiers temporaires si demandé
        if not args.keep_temp and os.path.exists(args.temp_dir):
            logging.info(f"Suppression du dossier temporaire {args.temp_dir}")
            shutil.rmtree(args.temp_dir)
        elif args.keep_temp:
            logging.info(f"Fichiers HTML conservés dans {args.temp_dir}")


if __name__ == "__main__":
    main()
