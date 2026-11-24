"""Print the text files of module directories, each under a header with its
path, for the LLM judges: dump_sources.py <root> <module dir>...

Paths are printed relative to <root>. Translations, images and other binary
files are left out.
"""
import sys
from pathlib import Path

SKIP_DIRS = {'i18n', '__pycache__'}
TEXT = {'.py', '.xml', '.csv', '.js', '.scss', '.css', '.md', '.rst', '.txt', '.json', '.html'}

root = Path(sys.argv[1]).resolve()
for module in sys.argv[2:]:
    module = Path(module).resolve()
    for path in sorted(module.rglob('*')):
        if not path.is_file() or path.suffix not in TEXT:
            continue
        if SKIP_DIRS & set(path.relative_to(module).parts):
            continue
        rel = path.relative_to(root)
        text = path.read_text(errors='replace')
        print(f'===== {rel} =====')
        print(text if text.endswith('\n') else text + '\n')
