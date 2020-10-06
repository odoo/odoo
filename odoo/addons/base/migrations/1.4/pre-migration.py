# Copyright 2020, Mtnet Services, S.A. de C.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(cr, installed_version):
	openupgrade.update_module_names(cr, [('iho_security','iho')], True)
	# env.cr.execute('DELETE FROM res_partner_bank WHERE partner_id IS NULL;')
