# Based on Florent Xicluna original code. Copyright Wingo SA
# Adapted by Nicolas Bessi. Copyright Camptocamp SA
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

import locale
import os
import platform
import subprocess
from functools import lru_cache

from odoo import release
from odoo.tools.config import config


def _get_output(cmd):
    bindir = config["root_path"]
    p = subprocess.Popen(
        cmd, shell=True, cwd=bindir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    return p.communicate()[0].rstrip()


@lru_cache(maxsize=1)
def get_server_environment():
    # inspired by server/bin/service/web_services.py
    try:
        rev_id = "git:{}".format(_get_output("git rev-parse HEAD"))
    except Exception:
        try:
            rev_id = "bzr: {}".format(_get_output("bzr revision-info"))
        except Exception:
            rev_id = "Can not retrieve revison from git or bzr"

    os_lang = ".".join([x for x in locale.getlocale() if x])
    if not os_lang:
        os_lang = "NOT SET"
    if os.name == "posix" and platform.system() == "Linux":
        lsbinfo = _get_output("lsb_release -a")
    else:
        lsbinfo = "not lsb compliant"
    return (
        ("platform", platform.platform()),
        ("os.name", os.name),
        ("lsb_release", lsbinfo),
        ("release", platform.release()),
        ("version", platform.version()),
        ("architecture", platform.architecture()[0]),
        ("locale", os_lang),
        ("python", platform.python_version()),
        ("odoo", release.version),
        ("revision", rev_id),
    )
