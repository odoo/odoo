# Copyright (C) 2009-Today - Akretion (<http://www.akretion.com>).
# @author Gabriel C. Stabel - Akretion
# @author Renato Lima <renato.lima@akretion.com.br>
# @author Raphael Valyi <raphael.valyi@akretion.com>
# @author Magno Costa <magno.costa@akretion.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from erpbrasil.base.fiscal import cnpj_cpf, ie

from odoo import _
from odoo.exceptions import ValidationError


def check_ie(env, inscr_est, state, country):
    """
    Checks if 'Inscrição Estadual' field is valid
    using erpbrasil library
    :param env:
    :param inscr_est:
    :param state:
    :param country:
    :return:
    """
    if env and inscr_est and state and country:
        if not country == env.ref("base.br"):
            return  # skip
        disable_ie_validation = env["ir.config_parameter"].sudo().get_param(
            "l10n_br_base.disable_ie_validation", default=False
        ) or env.context.get("disable_ie_validation")

        if disable_ie_validation:
            return  # skip
            # TODO: em aberto debate sobre:
            #  Se no caso da empresa ser 'isenta' do IE o campo
            #  deve estar vazio ou pode ter algum valor como abaixo
        if inscr_est in ("isento", "isenta", "ISENTO", "ISENTA"):
            return  # skip
        if not ie.validar(state.code.lower(), inscr_est):
            raise ValidationError(
                _(
                    "Estadual Inscription %(inscr)s Invalid for State %(state)s!",
                    inscr=inscr_est,
                    state=state.name,
                )
            )


def check_cnpj_cpf(env, cnpj_cpf_value, country):
    """
    Check CNPJ or CPF is valid using erpbrasil library
    :param env:
    :param cnpj_cpf_value:
    :param country:
    :return:
    """
    if env and cnpj_cpf_value and country:
        if country == env.ref("base.br"):
            disable_cpf_cnpj_validation = env["ir.config_parameter"].sudo().get_param(
                "l10n_br_base.disable_cpf_cnpj_validation", default=False
            ) or env.context.get("disable_cpf_cnpj_validation")

            if not disable_cpf_cnpj_validation:
                if not cnpj_cpf.validar(cnpj_cpf_value):
                    # Removendo . / - para diferenciar o CNPJ do CPF
                    # 62.228.384/0001-51 -CNPJ
                    # 62228384000151 - CNPJ
                    # 765.865.078-12 - CPF
                    # 76586507812 - CPF
                    document = "CPF"
                    if (
                        len("".join(char for char in cnpj_cpf_value if char.isdigit()))
                        == 14
                    ):
                        document = "CNPJ"

                    raise ValidationError(
                        _(
                            "%(d_type)s %(d_id)s is invalid!",
                            d_type=document,
                            d_id=cnpj_cpf_value,
                        )
                    )
