import re
import csv
import os
import sys
import argparse
import logging
import nltk
from bs4 import BeautifulSoup
from collections import Counter
from nltk.util import ngrams
from nltk.corpus import stopwords
from typing import Dict, Any, List
from urllib.parse import urljoin, urlparse


def ensure_nltk_resources():
    """S'assure que les ressources NLTK nécessaires sont présentes.
    Tente de télécharger `stopwords` et `punkt` si manquants.
    Silence les erreurs réseau et continue avec des valeurs par défaut minimales.
    """
    try:
        stopwords.words('french')
    except LookupError:
        try:
            nltk.download('stopwords')
        except Exception:
            logging.warning("Impossible de télécharger 'stopwords' NLTK; utilisation d'une liste minimale.")

    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt')
        except Exception:
            logging.warning("Impossible de télécharger 'punkt' NLTK; segmentation simple utilisée.")


ensure_nltk_resources()


try:
    STOPWORDS = set(stopwords.words('french'))
except Exception:
    # Liste minimale si NLTK indisponible
    STOPWORDS = set([])

# Stopwords étendus français pour filtrer les mots non significatifs
# Inclut pronoms, démonstratifs, conjonctions, prépositions communes
STOPWORDS_EXTENDED = STOPWORDS.union({
    # Pronoms
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "on", "moi", "toi", "lui", "nous", "vous", "eux",
    # Démonstratifs
    "ce", "cet", "cette", "ces", "celui", "celle", "ceux",
    # Possessifs
    "mon", "ton", "son", "ma", "ta", "sa", "mes", "tes", "ses", "notre", "votre", "leur",
    # Articles
    "un", "une", "des", "la", "le", "les", "l",
    # Prépositions communes
    "à", "de", "en", "pour", "par", "avec", "sans", "dans", "sous", "sur", "entre", "vers", "durant",
    # Conjonctions
    "et", "ou", "mais", "donc", "car", "ni", "que", "qui", "si", "comme", "alors", "lorsque",
    # Verbes auxiliaires
    "être", "avoir", "aller", "faire", "venir", "pouvoir", "devoir", "vouloir", "fallir", "sembler",
    "est", "sont", "était", "étaient", "a", "ont", "ai", "as", "ait", "aient", "suis", "es",
    "va", "vont", "allé", "allée", "allés", "allées", "vais", "vas",
    "fait", "font", "faits", "faisait", "faisaient", "fais", "fera", "feront",
    # Mots vides courants
    "ça", "ca", "là", "la", "ci", "pas", "plus", "moins", "très", "bien", "mal", "bon", "meilleur",
    # Abréviations et contractions
    "d'un", "d'une", "d'une", "qu'un", "c'est", "l'", "d'", "s'", "t'", "m'", "n'", "j'",
    # Autres mots peu significatifs
    "même", "autre", "tel", "telle", "tel", "etc", "même", "autant", "aussi", "seulement", "surtout",
    "quelque", "quelques", "quelqu'un", "aucun", "aucune", "nul", "nulle", "tout", "tous", "toute", "toutes"
}) 


########################################
# 1. Extraction du texte visible
########################################
def get_visible_text(soup):
    # supprimer scripts, styles, menus, footers, forms
    for tag in soup(["script", "style", "nav", "footer", "form", "noscript"]):
        tag.decompose()

    # texte brut
    text = soup.get_text(separator=" ")

    # nettoyage
    text = re.sub(r"\s+", " ", text).strip()
    return text


########################################
# 2. Extraction des n‑grams
########################################
def extract_ngrams(text, n_min=1, n_max=5):
    text = (text or "").lower()
    # autoriser chiffres et apostrophes dans les mots
    words = [w for w in re.findall(r"[0-9a-zA-Zàâçéèêëîïôûùüÿñæœ''-]+", text)
             if w and w.lower() not in STOPWORDS_EXTENDED and len(w) > 2]

    result: Dict[int, Counter] = {}
    for n in range(int(n_min), int(n_max) + 1):
        if len(words) < n:
            result[n] = Counter()
            continue
        ng = ngrams(words, n)
        freq = Counter([" ".join(g) for g in ng])
        # Filtrer les n-grams contenant des stopwords
        freq = Counter({k: v for k, v in freq.items() 
                       if not any(w.lower() in STOPWORDS_EXTENDED for w in k.split())})
        result[n] = freq
    return result


########################################
# 3. Extraction du maillage interne
########################################
def extract_internal_links(soup, base_url=None):
    links = set()
    base_netloc = None
    if base_url:
        try:
            base_netloc = urlparse(base_url).netloc
        except Exception:
            base_netloc = None

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue

        # normaliser lien relatif si base_url fourni
        if base_url:
            full = urljoin(base_url, href)
            parsed = urlparse(full)
            if parsed.netloc == base_netloc:
                links.add(full)
        else:
            # garder chemins relatifs (commencent par /)
            if href.startswith("/"):
                links.add(href)
    return sorted(links)


########################################
# 4. Extraction du CSV complet
########################################
def analyze_html(filepath, url=""):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        logging.error("Impossible de lire le fichier %s: %s", filepath, e)
        raise

    # parser lxml si disponible, sinon html.parser
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        logging.warning("Parser 'lxml' indisponible, utilisation de 'html.parser'.")
        soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    meta_desc = ""
    md_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if md_tag and md_tag.get("content"):
        meta_desc = md_tag["content"].strip()

    h1 = [h.get_text(strip=True) for h in soup.find_all("h1")]
    h2 = [h.get_text(strip=True) for h in soup.find_all("h2")]
    h3 = [h.get_text(strip=True) for h in soup.find_all("h3")]

    internal_anchors = [a.get_text(strip=True)
                        for a in soup.find_all("a") if a.get("href", "").startswith("#")]

    visible_text = get_visible_text(soup)

    ngram_freqs = extract_ngrams(visible_text)
    top_keywords = Counter()
    for freq in ngram_freqs.values():
        top_keywords.update(freq)
    top20 = [kw for kw, _ in top_keywords.most_common(20)]

    internal_links = extract_internal_links(soup, base_url=url if url else None)

    # phrases phares = phrases longues ou fréquentes — préférer nltk.sent_tokenize si disponible
    try:
        sentences = nltk.tokenize.sent_tokenize(visible_text, language='french') if visible_text else []
    except Exception:
        sentences = re.split(r"[.!?]+", visible_text) if visible_text else []
    phrases_phare = [s.strip() for s in sentences if len(s.split()) >= 6][:10]

    # conversion ngrams → texte brut (format lisible)
    parts: List[str] = []
    for n in sorted(ngram_freqs.keys()):
        freq = ngram_freqs[n]
        if not freq:
            continue
        items = ", ".join([f"{k}({v})" for k, v in freq.most_common(10)])
        parts.append(f"{n}-grams: {items}")
    ngram_text = "; ".join(parts)

    top_freqs = {k: v for k, v in top_keywords.items()}

    return {
        "URL": url,
        "Title": title,
        "H1": " | ".join(h1),
        "H2": " | ".join(h2),
        "H3": " | ".join(h3),
        "Meta description": meta_desc,
        "Ancres internes": " | ".join(internal_anchors),
        "Mots-clés dominants": " | ".join(top20),
        "N-grams": ngram_text,
        "Fréquences": str(top_freqs),
        "Liens internes": " | ".join(internal_links),
        "Phrases phares": " | ".join(phrases_phare),
        "Extrait de texte principal": (visible_text or "")[:600] + ("..." if visible_text and len(visible_text) > 600 else "")
    }


########################################
# 5. Export CSV
########################################
def export_csv(data, output="analyse.csv"):
    # s'assurer que le répertoire existe
    out_dir = os.path.dirname(os.path.abspath(output))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    fieldnames = list(data.keys())
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(data)

    logging.info("CSV écrit: %s", output)


########################################
# 6. MAIN
########################################
def _build_arg_parser():
    p = argparse.ArgumentParser(description="Analyse simple de structure HTML — extrait titres, n-grams, liens internes, etc.")
    p.add_argument("input", help="Fichier HTML en entrée")
    p.add_argument("-u", "--url", default="", help="URL de base (pour normaliser les liens internes)")
    p.add_argument("-o", "--output", default="analyse.csv", help="Fichier CSV de sortie")
    p.add_argument("--nmin", type=int, default=1, help="N-gram min (par défaut 1)")
    p.add_argument("--nmax", type=int, default=5, help="N-gram max (par défaut 5)")
    p.add_argument("--top", type=int, default=20, help="Nombre de mots-clés dominants à garder")
    p.add_argument("--verbose", action="store_true", help="Mode verbeux (logging DEBUG)")
    return p


def main(argv=None):
    args = _build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s: %(message)s")

    if not os.path.exists(args.input):
        logging.error("Fichier d'entrée introuvable: %s", args.input)
        sys.exit(2)

    data = analyze_html(args.input, url=args.url)
    export_csv(data, args.output)
    print(f"Analyse terminée → {args.output} généré")


if __name__ == "__main__":
    main()
