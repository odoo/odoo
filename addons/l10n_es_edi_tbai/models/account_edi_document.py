# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    def _prepare_jobs(self):
        """
        If there is a job to process that may already be part of the chain (posted invoice that timeout'ed),
        Re-places it at the beginning of the list.
        """
        # EXTENDS account_edi
        jobs = super()._prepare_jobs()
        if len(jobs) > 1:
            move_first_index = 0
            for index, job in enumerate(jobs):
                documents = job['documents']
                if any(d.edi_format_id.code == 'es_tbai' and d.state == 'to_send' and d.move_id.l10n_es_tbai_chain_index for d in documents):
                    move_first_index = index
                    break
            jobs = [jobs[move_first_index]] + jobs[:move_first_index] + jobs[move_first_index + 1:]

        return jobs
