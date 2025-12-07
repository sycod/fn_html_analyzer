#!/usr/bin/env python3
"""
clean_html.py
Nettoie un fichier HTML ou une URL en supprimant scripts, styles, imports CSS, attributs inline style et handlers on*.
Usage:
  python3 clean_html.py --input input.html --output out.html
  python3 clean_html.py --url "https://example.com" --output out.html
Options:
  -i/--input    : chemin vers un fichier HTML local (optionnel si --url utilisé)
  -u/--url      : URL à récupérer (optionnel si --input utilisé)
  -o/--output   : chemin du fichier HTML nettoyé (si non fourni, calculé par défaut dans le dossier du script)
  --timeout     : seconds timeout pour la requête (défaut 10)
  --user-agent  : user-agent HTTP (défaut: simple UA)
  --keep-images : ne pas toucher aux balises <img> (par défaut elles sont conservées)
  --extract-css : si présent, extrait le contenu de <style> dans un fichier .css à côté du output
  --verbose     : mode verbeux

Le script nécessite les paquets Python : beautifulsoup4, requests
"""

from pathlib import Path
import argparse
import sys
from bs4 import BeautifulSoup, Comment


def looks_like_stylesheet_link(tag):
    if tag.name != 'link':
        return False
    rel = tag.get('rel')
    href = tag.get('href', '') or ''
    rel_text = ' '.join(rel) if rel else ''
    rel_text = rel_text.lower()
    href_l = href.lower()
    if 'stylesheet' in rel_text or 'import' in rel_text:
        return True
    if href_l.endswith('.css'):
        return True
    if tag.get('as', '').lower() == 'style':
        return True
    return False


def clean_soup(soup, keep_images=False, extract_css_path=None, verbose=False):
    # remove comments first
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        if verbose:
            print("Removing comment")
        comment.extract()

    # Optionally extract inline <style> into a CSS file
    css_accum = []
    for name in ('script', 'iframe', 'embed', 'object'):
        for tag in list(soup.find_all(name)):
            if verbose:
                print(f"Removing <{name}> tag")
            tag.decompose()
    # handle <style>
    for st in list(soup.find_all('style')):
        text = st.string or ''
        if extract_css_path and text.strip():
            css_accum.append(text)
        st.decompose()
    # link tags that are stylesheets/imports
    for tag in list(soup.find_all('link')):
        if looks_like_stylesheet_link(tag):
            if verbose:
                print("Removing <link> stylesheet/import", tag)
            tag.decompose()
    # remove meta refresh
    for m in list(soup.find_all('meta')):
        if m.get('http-equiv', '').lower() == 'refresh':
            if verbose:
                print("Removing meta refresh", m)
            m.decompose()
    # remove inline style attributes and event handlers
    for tag in soup.find_all(True):
        # skip images if user asked to keep them
        if keep_images and tag.name == 'img':
            # but still remove on* handlers from img
            attrs = list(tag.attrs.keys())
            for a in attrs:
                if a.lower().startswith('on'):
                    try:
                        del tag.attrs[a]
                    except KeyError:
                        pass
            continue
        if tag.has_attr('style'):
            if verbose:
                print(f"Removing style attr from <{tag.name}>")
            del tag['style']
        attrs = list(tag.attrs.keys())
        for a in attrs:
            if a.lower().startswith('on'):
                if verbose:
                    print(f"Removing event handler {a} from <{tag.name}>")
                try:
                    del tag.attrs[a]
                except KeyError:
                    pass

    # remove empty <div> elements (no text and no important children)
    for div in list(soup.find_all('div')):
        # if there's visible text inside, keep
        if div.get_text(strip=True):
            continue
        # if it contains images/embeds/objects/iframes, keep
        if div.find(['img', 'iframe', 'embed', 'object']):
            continue
        # Otherwise it's empty (or only contained comments which are already removed) -> remove
        if verbose:
            print("Removing empty <div>")
        div.decompose()

    # return cleaned soup and css content (if any)
    return soup, '\n\n'.join(css_accum) if css_accum else None


def fetch_url(url, timeout=10, user_agent=None):
    import requests
    headers = {}
    if user_agent:
        headers['User-Agent'] = user_agent
    else:
        headers['User-Agent'] = 'clean-html-bot/1.0 (+https://example.local)'
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Erreur lors de la récupération de l'URL {url}: {e}")
    # force decode as UTF-8 to ensure output is UTF-8
    try:
        text = r.content.decode('utf-8', errors='replace')
    except Exception:
        text = r.text
    return text


def _strip_empty_lines(text: str) -> str:
    """Remove lines that contain only whitespace."""
    if text is None:
        return text
    lines = text.splitlines()
    kept = [ln for ln in lines if ln.strip()]
    # preserve final newline
    return '\n'.join(kept) + ('\n' if kept else '')


def _default_output_path(args) -> Path:
    """Compute default output path according to rules:
    - default folder is same as this script
    - if input file provided: same name + _clean before extension
    - if URL provided: domain name.html; if exists, append _1, _2, ...
    """
    script_dir = Path(__file__).resolve().parent
    if args.input:
        inp = Path(args.input)
        stem = inp.stem
        suffix = inp.suffix if inp.suffix else '.html'
        filename = f"{stem}_clean{suffix}"
        return script_dir / filename
    # else URL
    from urllib.parse import urlparse
    parsed = urlparse(args.url)
    host = parsed.hostname or 'output'
    base = host
    suffix = '.html'
    candidate = script_dir / (base + suffix)
    i = 1
    while candidate.exists():
        candidate = script_dir / f"{base}_{i}{suffix}"
        i += 1
    return candidate


def main():
    p = argparse.ArgumentParser(description='Nettoie un fichier HTML (local ou URL)')
    p.add_argument('-i', '--input', help='Fichier HTML source (local)')
    p.add_argument('-u', '--url', help='URL à récupérer')
    p.add_argument('-o', '--output', help='Fichier HTML nettoyé (si non fourni, calculé par défaut)')
    p.add_argument('--timeout', type=int, default=10, help='Timeout pour requête HTTP (secondes)')
    p.add_argument('--user-agent', default=None, help='User-Agent HTTP à utiliser lors du fetch')
    p.add_argument('--keep-images', action='store_true', help='Ne pas supprimer les balises <img> (par défaut elles sont conservées)')
    p.add_argument('--extract-css', action='store_true', help='Extraire les <style> inline dans un fichier .css à côté de la sortie')
    p.add_argument('--verbose', action='store_true')
    args = p.parse_args()

    if not args.input and not args.url:
        print('Erreur: fournissez soit --input soit --url', file=sys.stderr)
        sys.exit(2)

    # determine output path (default in script folder if not provided)
    outp = Path(args.output) if args.output else _default_output_path(args)

    html = None
    if args.url:
        if args.verbose:
            print(f"Fetching URL: {args.url}")
        try:
            html = fetch_url(args.url, timeout=args.timeout, user_agent=args.user_agent)
        except Exception as e:
            print(str(e), file=sys.stderr)
            sys.exit(3)
    else:
        inp = Path(args.input)
        if not inp.exists():
            print(f"Erreur : fichier d'entrée introuvable: {inp}", file=sys.stderr)
            sys.exit(2)
        html = inp.read_text(encoding='utf-8', errors='replace')

    # parse
    soup = BeautifulSoup(html, 'html.parser')
    cleaned_soup, css_text = clean_soup(soup, keep_images=args.keep_images, extract_css_path=args.extract_css, verbose=args.verbose)

    # prepare output text, remove empty lines, force UTF-8 and replace invalid chars
    out_text = str(cleaned_soup)
    out_text = _strip_empty_lines(out_text)
    outp.write_text(out_text, encoding='utf-8', errors='replace')
    if args.verbose:
        print(f"Fichier nettoyé écrit dans : {outp}")

    # write css file if requested
    if args.extract_css and css_text:
        css_path = outp.with_suffix(outp.suffix + '.extracted.css')
        css_text = _strip_empty_lines(css_text)
        css_path.write_text(css_text, encoding='utf-8', errors='replace')
        if args.verbose:
            print(f"CSS inline extrait vers : {css_path}")


if __name__ == '__main__':
    main()