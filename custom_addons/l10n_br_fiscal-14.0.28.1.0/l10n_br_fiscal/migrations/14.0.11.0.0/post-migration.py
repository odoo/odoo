# Copyright 2022 Engenere - Felipe Motter Pereira
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import logging
import os

from openupgradelib import openupgrade

from odoo import SUPERUSER_ID, api
from odoo.tools import pycompat
from odoo.tools.misc import file_open

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    module = "l10n_br_fiscal"
    pathname = os.path.join(module, "data/l10n_br_fiscal.ncm.csv")
    with file_open(pathname, "rb") as fp:
        convert_csv_import_by_line(
            env.cr, module, pathname, fp.read(), None, mode="init", noupdate=True
        )


def convert_csv_import_by_line(
    cr, module, fname, csvcontent, idref=None, mode="init", noupdate=False
):
    """
    Same as tools.convert_csv_import but try line by line and log instead
    of failing on error (exiting NCM)
    """
    filename, _ext = os.path.splitext(os.path.basename(fname))
    model = filename.split("-")[0]
    reader = pycompat.csv_reader(io.BytesIO(csvcontent), quotechar='"', delimiter=",")
    fields = next(reader)

    context = {
        "mode": mode,
        "module": module,
        "install_module": module,
        "install_filename": fname,
        "noupdate": noupdate,
    }
    env = api.Environment(cr, SUPERUSER_ID, context)
    for line in reader:
        try:
            result = env[model].load(fields, [line])
            if any(msg["type"] == "error" for msg in result["messages"]):
                # Report failed import and abort module install
                warning_msg = "\n".join(msg["message"] for msg in result["messages"])
                _logger.warning(warning_msg)
        except Exception:
            pass
