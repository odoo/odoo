# Copyright 2019 Akretion - Renato Lima <renato.lima@akretion.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime
from os import environ

from decorator import decorate
from erpbrasil.base import misc

from odoo.tests import SavepointCase
from odoo.tools import config as odooconfig

from odoo.addons.l10n_br_fiscal.models.ibpt import (
    DeOlhoNoImposto,
    get_ibpt_product,
    get_ibpt_service,
)

_logger = logging.getLogger(__name__)


def _not_every_day_test(method, self, modulo=7, remaining=0):
    if datetime.now().day % modulo == remaining or environ.get("CI_FORCE_IBPT"):
        return method(self)
    else:
        return lambda: _logger.info(
            f"Skipping test today because datetime.now().day % {modulo} != {remaining}"
        )


def not_every_day_test(method):
    """
    Decorate test methods to query the IBPT only
    1 day out of 7 and skip tests otherwise.
    Indeed the IBPT webservice often returns errors and it sucks
    to crash the entire l10n-brazil test suite because of this.
    the CI_FORCE_IBPT env var can be set to force the test anyhow.
    """
    return decorate(method, _not_every_day_test)


def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def ok(self):
            return True

        def json(self):
            return self.json_data

    # the same as rates during 2 days:
    return MockResponse(
        {
            "Codigo": "85030010",
            "UF": "ES",
            "EX": 0,
            "Descricao": "Partes de motores/geradores de pot<=75kva",
            "Nacional": 16.67,
            "Estadual": 25.0,
            "Importado": 23.98,
            "Municipal": 0.0,
            "Tipo": "0",
            "VigenciaInicio": "20/05/2023",
            "VigenciaFim": "30/06/2023",
            "Chave": "FADD79",
            "Versao": "23.1.F",
            "Fonte": "IBPT/empresometro.com.br",
            "Valor": 0.0,
            "ValorTributoNacional": 0.0,
            "ValorTributoEstadual": 0.0,
            "ValorTributoImportado": 0.0,
            "ValorTributoMunicipal": 0.0,
        },
        200,
    )


class TestIbpt(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls._create_compay()
        cls._switch_user_company(cls.env.user, cls.company)
        cls.product_tmpl_model = cls.env["product.template"]
        cls.tax_estimate_model = cls.env["l10n_br_fiscal.tax.estimate"]
        cls.ncm_model = cls.env["l10n_br_fiscal.ncm"]
        cls.nbs_model = cls.env["l10n_br_fiscal.nbs"]

    @classmethod
    def _switch_user_company(cls, user, company):
        """Add a company to the user's allowed & set to current."""
        user.write(
            {
                "company_ids": [(6, 0, (company + user.company_ids).ids)],
                "company_id": company.id,
            }
        )

    @classmethod
    def _check_ibpt_api(cls, company, ncm_nbs):
        """Check if IBPT API Webservice is online"""
        result = False
        try:
            config = DeOlhoNoImposto(
                company.ibpt_token,
                misc.punctuation_rm(company.cnpj_cpf),
                company.state_id.code,
                odooconfig.get("ibpt_request_timeout")
                or cls.env["ir.config_parameter"]
                .sudo()
                .get_param("ibpt_request_timeout"),
            )
            if ncm_nbs._name == "l10n_br_fiscal.ncm":
                result = bool(get_ibpt_product(config, ncm_nbs.code_unmasked))

            if ncm_nbs._name == "l10n_br_fiscal.nbs":
                result = bool(get_ibpt_service(config, ncm_nbs.code_unmasked))
        except Exception:
            result = False
        return result

    @classmethod
    def _create_compay(cls):
        """Create and config Company to test IBPT API"""
        # Creating a company
        company = cls.env["res.company"].create(
            {
                "name": "Company Test Fiscal BR",
                "cnpj_cpf": "02.960.895/0002-12",
                "country_id": cls.env.ref("base.br").id,
                "state_id": cls.env.ref("base.state_br_es").id,
                "ibpt_api": True,
                "ibpt_update_days": 0,
                "ibpt_token": (
                    "dsaaodNP5i6RCu007nPQjiOPe5XIefnx"
                    "StS2PzOV3LlDRVNGdVJ5OOUlwWZhjFZk"
                ),
            }
        )

        if not cls._check_ibpt_api(company, cls.env.ref("l10n_br_fiscal.ncm_85030010")):
            company.write({"ibpt_api": False})

        return company

    @classmethod
    def _create_product_tmpl(cls, name, ncm):
        """Create products related with NCM"""
        product = cls.product_tmpl_model.create({"name": name, "ncm_id": ncm.id})
        return product

    @classmethod
    def _create_service_tmpl(cls, name, nbs):
        """Create services related with NBS"""
        product = cls.product_tmpl_model.create({"name": name, "nbs_id": nbs.id})
        return product
