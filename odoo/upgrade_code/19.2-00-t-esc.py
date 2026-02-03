# Replaces the t-esc directive by t-out in preparation for the OWL3 migration

import re
import logging

_logger = logging.getLogger(__name__)


def upgrade(file_manager):
    files = [file for file in file_manager if file.path.suffix == '.xml']
    if not files:
        return

    reg_t_esc = re.compile(r"""\bt-esc=""")

    for fileno, file in enumerate(files, start=1):
        try:
            content = file.path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            # For file enterprise/l10n_cl_edi_factoring/template/aec_template.xml
            _logger.warning("upgrade_code: skipping non-utf8 file %s (%s)", file.path, e)

        # update
        content = reg_t_esc.sub(r't-out=', content)

        file.content = content
        file_manager.print_progress(fileno, len(files))
