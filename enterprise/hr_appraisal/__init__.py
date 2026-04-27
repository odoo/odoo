# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard


def _generate_assessment_note_ids(env):
    default_notes = env['res.company']._get_default_assessment_note_ids()
    default_appraisal_template = env['res.company']._get_default_appraisal_template()
    default_confirmation_mail_template = env['res.company']._get_default_appraisal_confirm_mail_template()

    env['res.company'].search([]).write({
        'assessment_note_ids': default_notes,
        'appraisal_template_id': default_appraisal_template,
        'appraisal_confirm_mail_template': default_confirmation_mail_template.id,
    })
