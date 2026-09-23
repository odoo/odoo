# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Load probe credentials from a private file outside the repository.

Credentials must never be committed: the Nuonuo ones reach a production gateway.
Both probes call load() first, so variables already exported in the shell win,
and anything missing is read from ~/.config/l10n_cn_edi/probe.env (KEY=VALUE lines).
"""
import os
import stat
import sys

PATH = os.path.expanduser(os.environ.get('L10N_CN_EDI_PROBE_ENV', '~/.config/l10n_cn_edi/probe.env'))


def load(path=PATH):
    if not os.path.exists(path):
        return
    if os.stat(path).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        sys.exit(f'refusing {path}: readable by others, run chmod 600 on it')
    with open(path, encoding='utf-8') as env_file:
        for line in env_file:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())
