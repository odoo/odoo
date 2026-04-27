# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def _generate_payroll_document_folders(env):
    env['res.company'].search([])._generate_payroll_document_folders()
