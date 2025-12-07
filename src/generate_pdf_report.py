#!/usr/bin/env python3
"""
generate_pdf_report.py
Génère un rapport PDF complet à partir des résultats d'analyse.

Usage:
    python3 generate_pdf_report.py --analysis-dir ./analyse_results --output rapport.pdf

Options:
  --analysis-dir / -d : Dossier contenant les résultats d'analyse
  --output / -o       : Fichier PDF de sortie (défaut: rapport_analyse.pdf)
  --verbose / -v      : Mode verbeux
"""

import os
import sys
import argparse
import logging
import csv
from pathlib import Path
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    import pandas as pd
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Erreur: reportlab n'est pas installé. Installez-le avec: pip install reportlab")
    sys.exit(1)


def setup_logger(verbose=False):
    """Configure le logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s"
    )


def read_analysis_csv(csv_path):
    """Lit le CSV d'analyse complète."""
    df = pd.read_csv(csv_path)
    return df


def read_aggregated_csv(csv_path):
    """Lit le CSV d'agrégation globale."""
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def create_pdf_report(analysis_dir, output_pdf):
    """Crée le rapport PDF complet."""
    analysis_path = Path(analysis_dir)
    
    # Vérifier l'existence des fichiers
    csv_complete = analysis_path / "analyse_complete.csv"
    csv_global = analysis_path / "analyse_globale.csv"
    viz_dir = analysis_path / "visualisations"
    
    if not csv_complete.exists():
        logging.error(f"Fichier manquant: {csv_complete}")
        sys.exit(1)
    
    if not csv_global.exists():
        logging.error(f"Fichier manquant: {csv_global}")
        sys.exit(1)
    
    logging.info(f"Création du rapport PDF: {output_pdf}")
    
    # Lire les données
    df_complete = read_analysis_csv(csv_complete)
    data_global = read_aggregated_csv(csv_global)
    
    # Créer le document PDF
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=1*inch,
        bottomMargin=0.75*inch
    )
    
    # Styles personnalisés
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
    
    # Contenu du document
    content = []
    
    # ========== PAGE 1: INTRODUCTION ==========
    content.append(Paragraph("RAPPORT D'ANALYSE SÉMANTIQUE WEB", title_style))
    content.append(Spacer(1, 0.3*inch))
    
    # Date et heure
    date_str = datetime.now().strftime("%d %B %Y à %H:%M:%S")
    content.append(Paragraph(f"<i>Généré le {date_str}</i>", styles['Normal']))
    content.append(Spacer(1, 0.5*inch))
    
    # Introduction
    intro_text = """
    Ce rapport présente une analyse complète de la structure sémantique et du contenu web des domaines étudiés.
    L'analyse inclut l'extraction de mots-clés dominants, la génération de n-grams, l'identification de liens internes,
    et une agrégation globale des thèmes majeurs identifiés.
    """
    content.append(Paragraph(intro_text, normal_style))
    content.append(Spacer(1, 0.3*inch))
    
    # Liste des URLs étudiées
    content.append(Paragraph("URLs et Domaines Étudiés", heading_style))
    
    urls = df_complete['URL'].unique()
    unique_domains = set()
    url_data = [['#', 'Domaine', 'URL']]
    
    for i, url in enumerate(urls, 1):
        if pd.notna(url) and str(url) != 'ERREUR':
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
            ('FONTSIZE', (0, 0), (-1, 0), 10),
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
    
    # ========== PAGES: ANALYSES UNITAIRES ==========
    content.append(Paragraph("Analyses Unitaires par Page", heading_style))
    content.append(Spacer(1, 0.2*inch))
    
    for idx, row in df_complete.iterrows():
        url = row.get('URL', f'Page {idx+1}')
        
        if str(url).startswith('ERREUR'):
            continue
        
        # Titre de la page
        page_title = str(url).split('/')[-1] or str(url)[:50]
        content.append(Paragraph(f"Page {idx+1}: {page_title}", styles['Heading3']))
        
        # Tableau des données
        page_data = [
            ['Propriété', 'Contenu'],
            ['URL', str(url)[:70]],
            ['Title', str(row.get('Title', 'N/A'))[:70]],
            ['H1', str(row.get('H1', 'N/A'))[:70]],
            ['H2', str(row.get('H2', 'N/A'))[:70]],
            ['H3', str(row.get('H3', 'N/A'))[:70]],
            ['Meta Description', str(row.get('Meta description', 'N/A'))[:70]],
            ['Mots-clés dominants', str(row.get('Mots-clés dominants', 'N/A'))[:70]],
            ['Liens internes', str(len([l for l in str(row.get('Liens internes', '')).split('|') if l.strip()]))],
        ]
        
        page_table = Table(page_data, colWidths=[1.5*inch, 4*inch])
        page_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e75b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f0f0')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
        ]))
        content.append(page_table)
        content.append(Spacer(1, 0.2*inch))
        
        if (idx + 1) % 3 == 0:
            content.append(PageBreak())
    
    content.append(PageBreak())
    
    # ========== PAGE: ANALYSE GLOBALE ==========
    content.append(Paragraph("Analyse Globale - Top 50 Mots-clés et N-grams", heading_style))
    content.append(Spacer(1, 0.2*inch))
    
    # Tableau d'agrégation
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
    
    conclusion_text = f"""
    <b>Résumé de l'analyse:</b><br/><br/>
    
    Cette analyse sémantique a examiné <b>{len(urls)} URL(s)</b> réparties sur <b>{len(unique_domains)} domaine(s)</b>.
    Au total, <b>{len(df_complete)} page(s)</b> ont été analysées avec succès.<br/><br/>
    
    <b>Principaux enseignements:</b><br/>
    • Le terme le plus fréquent est <b>"{data_global[0]['Mot-clé / N-gram']}"</b> avec 
    <b>{data_global[0]['Occurrences']} occurrences</b><br/>
    • Les analyses unitaires révèlent des structures HTML variées et des stratégies de contenu distinctes<br/>
    • L'agrégation globale identifie les thèmes centraux qui unissent les différentes pages<br/>
    • Les visualisations mettent en lumière les co-occurrences sémantiques clés<br/><br/>
    
    <b>Recommandations:</b><br/>
    • Examiner le réseau sémantique pour identifier les clusters thématiques<br/>
    • Comparer les mots-clés unitaires avec le top global pour détecter les divergences<br/>
    • Analyser la heatmap pour évaluer la cohérence sémantique du site<br/>
    • Utiliser le word cloud pour visualiser l'identité thématique globale<br/><br/>
    
    <i>Ce rapport a été généré automatiquement le {datetime.now().strftime("%d %B %Y à %H:%M:%S")}
    par l'outil d'analyse sémantique sycod.</i>
    """
    
    content.append(Paragraph(conclusion_text, normal_style))
    
    # Construire le PDF
    try:
        doc.build(content)
        logging.info(f"✓ Rapport PDF généré: {output_pdf}")
        print(f"\n{'='*60}")
        print(f"✓ Rapport PDF généré avec succès!")
        print(f"{'='*60}")
        print(f"Fichier: {output_pdf}")
        print(f"Taille: {Path(output_pdf).stat().st_size / 1024 / 1024:.2f} MB")
        print(f"{'='*60}")
    except Exception as e:
        logging.error(f"Erreur lors de la génération du PDF: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Génère un rapport PDF complet à partir des résultats d'analyse"
    )
    parser.add_argument('-d', '--analysis-dir', required=True, 
                        help='Dossier contenant les résultats d\'analyse')
    parser.add_argument('-o', '--output', default='rapport_analyse.pdf',
                        help='Fichier PDF de sortie (défaut: rapport_analyse.pdf)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    
    args = parser.parse_args()
    
    setup_logger(args.verbose)
    
    if not os.path.exists(args.analysis_dir):
        logging.error(f"Dossier d'analyse introuvable: {args.analysis_dir}")
        sys.exit(1)
    
    create_pdf_report(args.analysis_dir, args.output)


if __name__ == "__main__":
    main()
