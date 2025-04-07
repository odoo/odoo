# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import odoo.tools.safe_eval as safe_eval

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class MailingFilter(models.Model):
    """ This model stores mass mailing or marketing campaign domain as filters
    (quite similar to 'ir.filters' but dedicated to mailing apps). Frequently
    used domains can be reused easily. """
    _name = 'mailing.filter'
    _description = 'Mailing Favorite Filters'
    _order = 'create_date DESC'

    # override create_uid field to display default value while creating filter from 'Configuration' menus
    create_uid = fields.Many2one('res.users', 'Saved by', index=True, readonly=True, default=lambda self: self.env.user)
    name = fields.Char(string='Filter Name', required=True)
    mailing_domain = fields.Char(string='Filter Domain', required=True)
    mailing_model_id = fields.Many2one('ir.model', string='Recipients Model', required=True, ondelete='cascade')
    mailing_model_name = fields.Char(string='Recipients Model Name', related='mailing_model_id.model')

    @staticmethod
    def _evaluate_domain(domain):
        """Evaluate domain string as python code using safe_eval

        :param str domain: the domain to evaluate
        :returns: evaluation context given to safe_eval
        :rtype: dict
        """
        # to_utc is a purely JS concept where datetime is localized by default
        # as that is the default in python, and to_utc is undefined, we can disregard it
        domain = domain.replace('.to_utc()', '')
        evaluated_domain = safe_eval.safe_eval(domain, {
            'context_today': safe_eval.datetime.datetime.today,
            'datetime': safe_eval.datetime,
            'dateutil': safe_eval.dateutil,
            'relativedelta': safe_eval.dateutil.relativedelta.relativedelta,
            'time': safe_eval.time,
        })
        assert isinstance(evaluated_domain, list)
        return evaluated_domain

    @staticmethod
    def _combine_dynamic_domains(domain_a, domain_b):
        """Combines two string domains that contain non-literals."""
        domains = [domain_a, domain_b]
        parsed_domains = []
        for domain in domains:
            try:
                parsed_domain = ast.parse(domain, mode="eval", filename="domain")
                # only manipulate list elements
                if not isinstance(parsed_domain.body, ast.List):
                    raise UserError(_("A valid domain is expected, got: %(domain_expression)s", domain_expression=domain))
                parsed_domains.append(parsed_domain)
            except SyntaxError as se:
                raise UserError(
                    _("Invalid domain %(domain_expression)s: %(syntax_error)s", domain_expression=domain, syntax_error=se)
                )
        new_domain = ast.parse("[]", mode="eval")
        # add as many "AND" as domain that need to be joined
        new_domain.body.elts.extend([ast.Constant('&')] * (sum(bool(domain.body.elts) for domain in parsed_domains) - 1))
        new_domain.body.elts.extend(element for domain in parsed_domains for element in domain.body.elts)
        return ast.unparse(new_domain)

    @api.constrains('mailing_domain', 'mailing_model_id')
    def _check_mailing_domain(self):
        """ Check that if the mailing domain is set, it is a valid one """
        for mailing_filter in self:
            if mailing_filter.mailing_domain != "[]":
                try:
                    self.env[mailing_filter.mailing_model_id.model].search_count(self._evaluate_domain(mailing_filter.mailing_domain))
                except:
                    raise ValidationError(
                        _("The filter domain is not valid for this recipients.")
                    )
