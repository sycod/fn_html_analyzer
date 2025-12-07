#!/usr/bin/env python3
"""
batch_clean.py
Lit un fichier contenant une URL par ligne et exécute `clean_html.py` pour chacune.
Usage:
  python3 batch_clean.py --list urls.txt [--out-dir /path] [--concurrency 4] [--delay 0.5] [--verbose]

Options:
  --list / -l       : fichier texte avec une URL par ligne (commentaires commençant par # ignorés)
  --out-dir / -d    : (optionnel) dossier de sortie pour les fichiers nettoyés. Si absent, laisse `clean_html.py` créer les noms par défaut
  --concurrency / -c: nombre de jobs parallèles (défaut 1 = séquentiel)
  --delay / -D      : délai (secondes) entre lancements (utile en séquentiel ou pour limiter charge)
  --verbose / -v    : mode verbeux

Le script invoque `clean_html.py` avec le même interpréteur Python que celui qui lance ce script.
"""

from pathlib import Path
import argparse
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import time


def read_urls(file_path: Path):
    lines = file_path.read_text(encoding='utf-8', errors='replace').splitlines()
    urls = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        urls.append(ln)
    return urls


def make_output_for_url(out_dir: Path, url: str) -> Path:
    """Return a non-colliding Path based on domain name.
    If out_dir is None, return None to let clean_html decide its default.
    """
    if out_dir is None:
        return None
    parsed = urlparse(url)
    host = parsed.hostname or 'output'
    base = host
    suffix = '.html'
    candidate = out_dir / (base + suffix)
    i = 1
    while candidate.exists():
        candidate = out_dir / f"{base}_{i}{suffix}"
        i += 1
    return candidate


def run_one(clean_script: Path, python_exe: str, url: str, out_path: Path | None, verbose: bool):
    cmd = [python_exe, str(clean_script), '--url', url]
    if out_path:
        cmd += ['--output', str(out_path)]
    if verbose:
        print('Running:', ' '.join(cmd))
    try:
        r = subprocess.run(cmd, capture_output=not verbose, text=True)
    except Exception as e:
        return (url, False, f'Failed to start process: {e}')
    if r.returncode != 0:
        out = r.stderr if not verbose else ''
        return (url, False, out or f'Exit {r.returncode}')
    return (url, True, '')


def main():
    p = argparse.ArgumentParser(description='Batch run clean_html.py on a list of URLs')
    p.add_argument('-l', '--list', required=True, help='Fichier texte avec une URL par ligne')
    p.add_argument('-d', '--out-dir', default=None, help='Dossier de sortie (optionnel)')
    p.add_argument('-c', '--concurrency', type=int, default=1, help='Nombre de jobs en parallèle (1 = séquentiel)')
    p.add_argument('-D', '--delay', type=float, default=0.0, help='Délai (s) entre lancements')
    p.add_argument('-v', '--verbose', action='store_true')
    args = p.parse_args()

    list_path = Path(args.list)
    if not list_path.exists():
        print(f'Fichier de liste introuvable: {list_path}', file=sys.stderr)
        sys.exit(2)

    urls = read_urls(list_path)
    if not urls:
        print('Aucune URL valide trouvée dans la liste.', file=sys.stderr)
        sys.exit(0)

    clean_script = Path(__file__).resolve().parent / 'clean_html.py'
    if not clean_script.exists():
        print(f"clean_html.py introuvable dans le même dossier que ce script: {clean_script}", file=sys.stderr)
        sys.exit(2)

    python_exe = sys.executable

    out_dir = Path(args.out_dir).resolve() if args.out_dir else None
    if out_dir and not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    if args.concurrency <= 1:
        # séquentiel
        for url in urls:
            target = make_output_for_url(out_dir, url)
            if args.verbose:
                print(f'Processing {url} -> {target or "(default)"}')
            res = run_one(clean_script, python_exe, url, target, args.verbose)
            results.append(res)
            if args.delay:
                time.sleep(args.delay)
    else:
        # concurrent
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            future_to_url = {}
            for url in urls:
                target = make_output_for_url(out_dir, url)
                future = ex.submit(run_one, clean_script, python_exe, url, target, args.verbose)
                future_to_url[future] = url
                if args.delay:
                    time.sleep(args.delay)
            for fut in as_completed(future_to_url):
                results.append(fut.result())

    # summary
    success = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    print('\nBatch finished. Summary:')
    print(f'  total: {len(results)}')
    print(f'  ok   : {len(success)}')
    print(f'  failed: {len(failed)}')
    if failed:
        print('\nFailed items:')
        for url, ok, err in failed:
            print('-', url, '->', err.strip() if isinstance(err, str) else err)


if __name__ == '__main__':
    main()
