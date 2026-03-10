# Copyright (C) 2015  Luis Felipe Miléo - KMEE
# Copyright (C) 2019  Renato Lima - Akretion
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from collections import namedtuple

import requests

from odoo import _
from odoo.exceptions import UserError

WS_SERVICOS = 0
WS_PRODUTOS = 1

WS_IBPT = {
    WS_SERVICOS: "https://apidoni.ibpt.org.br/api/v1/servicos?",
    WS_PRODUTOS: "https://apidoni.ibpt.org.br/api/v1/produtos?",
}


DeOlhoNoImposto = namedtuple("Config", "token cnpj uf ibpt_request_timeout")


def _request(ws_url, params, ibpt_request_timeout=30):
    try:
        response = requests.get(
            ws_url, params=params, timeout=int(ibpt_request_timeout)
        )
        if response.ok:
            data = response.json()
            return namedtuple("Result", [k.lower() for k in data.keys()])(
                **{k.lower(): v for k, v in data.items()}
            )
        elif response.status_code == requests.codes.forbidden:
            raise UserError(
                _(
                    "IBPT Forbidden - token=%(token)s, cnpj=%(cnpj)s, UF=%(uf)s",
                    token=params.get("token"),
                    cnpj=params.get("cnpj"),
                    uf=params.get("uf"),
                )
            )
        elif response.status_code == requests.codes.not_found:
            raise UserError(_("IBPT URL not found - {!r}").format(ws_url))
        elif response.status_code == requests.codes.service_unavailable:
            raise UserError(_("IBPT Service Unavailable - {!r}").format(ws_url))
    except Exception as e:
        raise UserError(_("Error in the request: {}").format(e)) from e


def get_ibpt_product(
    config, ncm, ex="0", reference="", description="", uom="", amount="0", gtin=""
):
    data = {
        "token": config.token,
        "cnpj": config.cnpj,
        "uf": config.uf,
        "codigo": ncm,
        "ex": ex,
        "codigoInterno": reference,
        "descricao": description,
        "unidadeMedida": uom,
        "valor": amount,
        "gtin": gtin,
    }

    return _request(WS_IBPT[WS_PRODUTOS], data, config.ibpt_request_timeout)


def get_ibpt_service(config, nbs, description="", uom="", amount="0"):
    data = {
        "token": config.token,
        "cnpj": config.cnpj,
        "codigo": nbs,
        "uf": config.uf,
        "descricao": description,
        "unidadeMedida": uom,
        "valor": amount,
    }

    return _request(WS_IBPT[WS_SERVICOS], data, config.ibpt_request_timeout)
