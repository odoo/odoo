#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2009-2010 Soluciones Tecnologócias Prisma S.A. All Rights Reserved.
# José Rodrigo Fernández Menegazzo, Soluciones Tecnologócias Prisma S.A.
# (http://www.solucionesprisma.com)
from odoo import api, SUPERUSER_ID

def load_translations(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('l10n_gt.cuentas_plantilla').process_coa_translations()
