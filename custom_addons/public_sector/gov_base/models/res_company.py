from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    cnpj_ug = fields.Char(string="CNPJ da Unidade Gestora", size=18)
    codigo_ug = fields.Char(string="Código UG", size=10)
    codigo_siafi = fields.Char(string="Código SIAFI Estadual", size=10)
    exercicio_fiscal = fields.Integer(
        string="Exercício Fiscal Ativo",
        default=lambda self: fields.Date.today().year,
    )

    # Backend Theme Customization
    theme_color_brand_primary = fields.Char(string="Cor Primária", default="#70AA87")
    theme_color_brand_secondary = fields.Char(string="Cor Secundária", default="#9FB38F")
    theme_color_webclient_bg = fields.Char(string="Cor de Fundo do Sistema", default="#C5BD99")
    theme_color_main_text = fields.Char(string="Cor do Texto Principal", default="#1C0F0E")
    theme_color_danger = fields.Char(string="Cor de Erro/Alerta", default="#DB5643")

    @api.model
    def _gov_base_sync_processo_rules(self):
        """Create/update gov.processo rules only when the model exists.

        This keeps gov_base installable before gov_processos is introduced.
        """
        model = self.env["ir.model"].sudo().search([("model", "=", "gov.processo")], limit=1)
        if not model:
            return True

        rule_model = self.env["ir.rule"].sudo()
        data_model = self.env["ir.model.data"].sudo()

        specs = [
            {
                "xml_name": "rule_gov_processo_operador",
                "name": "AGI Gov Processo / Operador - Somente UG do usuário",
                "domain_force": "[('ug_id','=',user.company_id.id)]",
                "group_xmlid": "gov_base.group_gov_operador",
            },
            {
                "xml_name": "rule_gov_processo_gestor",
                "name": "AGI Gov Processo / Gestor - Todas as UGs",
                "domain_force": "[(1,'=',1)]",
                "group_xmlid": "gov_base.group_gov_gestor",
            },
            {
                "xml_name": "rule_gov_processo_admin",
                "name": "AGI Gov Processo / Administrador - Acesso total",
                "domain_force": "[(1,'=',1)]",
                "group_xmlid": "gov_base.group_gov_admin",
            },
        ]

        for spec in specs:
            group = self.env.ref(spec["group_xmlid"])
            xmlid = f"gov_base.{spec['xml_name']}"
            existing_rule = self.env.ref(xmlid, raise_if_not_found=False)
            values = {
                "name": spec["name"],
                "model_id": model.id,
                "domain_force": spec["domain_force"],
                "groups": [(6, 0, [group.id])],
                "active": False,
                "perm_read": True,
                "perm_write": True,
                "perm_create": True,
                "perm_unlink": True,
            }

            if existing_rule and existing_rule._name == "ir.rule":
                existing_rule.sudo().write(values)
                rule = existing_rule
            else:
                rule = rule_model.create(values)

            imd = data_model.search(
                [("module", "=", "gov_base"), ("name", "=", spec["xml_name"])], limit=1
            )
            if imd:
                imd.write({"model": "ir.rule", "res_id": rule.id, "noupdate": True})
            else:
                data_model.create(
                    {
                        "module": "gov_base",
                        "name": spec["xml_name"],
                        "model": "ir.rule",
                        "res_id": rule.id,
                        "noupdate": True,
                    }
                )

        return True
