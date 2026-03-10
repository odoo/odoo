# Copyright (C) 2019 - Renato Lima Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import logging

from odoo import SUPERUSER_ID, _, api, tools

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Import XML data to change core data"""
    env = api.Environment(cr, SUPERUSER_ID, {})

    files = [
        "data/l10n_br_fiscal.cnae.csv",
        "data/l10n_br_fiscal.cfop.csv",
        "data/l10n_br_fiscal_cfop_data.xml",
        "data/l10n_br_fiscal.tax.ipi.control.seal.csv",
        "data/l10n_br_fiscal.tax.ipi.guideline.csv",
        "data/l10n_br_fiscal.tax.ipi.guideline.class.csv",
        "data/l10n_br_fiscal.tax.pis.cofins.base.csv",
        "data/l10n_br_fiscal.tax.pis.cofins.credit.csv",
        "data/l10n_br_fiscal.service.type.csv",
        "data/simplified_tax_data.xml",
        "data/operation_data.xml",
        "data/l10n_br_fiscal_tax_icms_data.xml",
    ]

    _logger.info(_("Loading l10n_br_fiscal fiscal files. It may take a minute..."))

    for file in files:
        tools.convert_file(
            cr,
            "l10n_br_fiscal",
            file,
            None,
            mode="init",
            noupdate=True,
            kind="init",
        )

    env.cr.execute("select demo from ir_module_module where name='l10n_br_fiscal';")
    is_demo = env.cr.fetchone()[0]
    if is_demo:
        demofiles = [
            "demo/l10n_br_fiscal.ncm-demo.csv",
            "demo/l10n_br_fiscal.nbm-demo.csv",
            "demo/l10n_br_fiscal.nbs-demo.csv",
            "demo/l10n_br_fiscal.cest-demo.csv",
            "demo/city_taxation_code_demo.xml",
            "demo/company_demo.xml",
            "demo/product_demo.xml",
            "demo/partner_demo.xml",
            "demo/fiscal_document_nfse_demo.xml",
            "demo/fiscal_operation_demo.xml",
            "demo/subsequent_operation_demo.xml",
            "demo/l10n_br_fiscal_document_email.xml",
            "demo/res_users_demo.xml",
            "demo/icms_tax_definition_demo.xml",
        ]

        # Load only demo CSV files with few lines instead of thousands
        # unless a flag mention the contrary
        short_files = {
            "load_ncm": "data/l10n_br_fiscal.ncm.csv",
            "load_nbm": "data/l10n_br_fiscal.nbm.csv",
            "load_nbs": "data/l10n_br_fiscal.nbs.csv",
            "load_cest": "data/l10n_br_fiscal.cest.csv",
        }

        for short_file in short_files.keys():
            if tools.config.get(short_file):
                demofiles.append(short_files[short_file])

        _logger.info(_("Loading l10n_br_fiscal demo files."))

        for f in demofiles:
            tools.convert_file(
                cr,
                "l10n_br_fiscal",
                f,
                None,
                mode="init",
                noupdate=True,
                kind="demo",
            )

    if not is_demo:
        prodfiles = []
        # Load full CSV files with few lines unless a flag
        # mention the contrary
        skip_prodfiles = {
            "skip_ncm": "data/l10n_br_fiscal.ncm.csv",
            "skip_nbm": "data/l10n_br_fiscal.nbm.csv",
            "skip_nbs": "data/l10n_br_fiscal.nbs.csv",
            "skip_cest": "data/l10n_br_fiscal.cest.csv",
        }

        for skip_prodfile in skip_prodfiles.keys():
            if not tools.config.get(skip_prodfile):
                prodfiles.append(skip_prodfiles[skip_prodfile])

        _logger.info(
            _(
                "Loading l10n_br_fiscal production files. It may take at least"
                " 3 minutes..."
            )
        )

        for f in prodfiles:
            tools.convert_file(
                cr,
                "l10n_br_fiscal",
                f,
                None,
                mode="init",
                noupdate=True,
                kind="init",
            )

    # Load post files
    posloadfiles = [
        "data/l10n_br_fiscal_icms_tax_definition_data.xml",
    ]

    _logger.info(_("Loading l10n_br_fiscal post init files. It may take a minute..."))

    for file in posloadfiles:
        tools.convert_file(
            cr,
            "l10n_br_fiscal",
            file,
            None,
            mode="init",
            noupdate=True,
            kind="init",
        )

    # Load post demo files
    if is_demo:
        posdemofiles = [
            "demo/fiscal_document_demo.xml",
        ]

        _logger.info(
            _("Loading l10n_br_fiscal post demo files. It may take a minute...")
        )

        for file in posdemofiles:
            tools.convert_file(
                cr,
                "l10n_br_fiscal",
                file,
                None,
                mode="demo",
                noupdate=True,
                kind="init",
            )
