from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class AccountTaxReport(models.Model):
    _name = "account.tax.report"
    _description = 'Account Tax Report'
    _order = 'country_id, name'

    name = fields.Char(string="Name", required=True, help="Name of this tax report")
    country_id = fields.Many2one(string="Country", comodel_name='res.country', required=True, default=lambda x: x.env.company.country_id.id, help="Country for which this report is available.")
    line_ids = fields.One2many(string="Report Lines", comodel_name='account.tax.report.line', inverse_name='report_id', help="Content of this tax report")
    root_line_ids = fields.One2many(string="Root Report Lines", comodel_name='account.tax.report.line', inverse_name='report_id', domain=[('parent_id', '=', None)], help="Subset of line_ids, containing the lines at the root of the report.")

    def write(self, vals):
        # Overridden so that we change the country _id of the existing tags
        # when writing the country_id of the report, or create new tags
        # for the new country if the tags are shared with some other report.

        if 'country_id' in vals:
            tags_cache = {}
            for record in self.filtered(lambda x: x.country_id.id != vals['country_id']):
                for line in record.line_ids:
                    if line.tag_ids:
                        #The tags for this country may have been created by a previous line in this loop
                        cache_key = (vals['country_id'], line.tag_name)
                        if cache_key not in tags_cache:
                            tags_cache[cache_key] = self.env['account.account.tag']._get_tax_tags(line.tag_name, vals['country_id'])

                        new_tags = tags_cache[cache_key]

                        if len(new_tags) == 2:
                            line._remove_tags_used_only_by_self()
                            line.write({'tag_ids': [(6, 0, new_tags.ids)]})

                        elif line.mapped('tag_ids.tax_report_line_ids.report_id').filtered(lambda x: x not in self):
                            line._remove_tags_used_only_by_self()
                            line.write({'tag_ids': [(5, 0, 0)] + line._get_tags_create_vals(line.tag_name, vals['country_id'], existing_tag=new_tags)})
                            tags_cache[cache_key] = line.tag_ids

                        else:
                            line.tag_ids.write({'country_id': vals['country_id']})

        return super(AccountTaxReport, self).write(vals)

    def copy(self, default=None):
        # Overridden from regular copy, since the ORM does not manage
        # the copy of the lines hierarchy properly (all the parent_id fields
        # need to be reassigned to the corresponding copies).

        copy_default = {k:v for k, v in default.items() if k != 'line_ids'} if default else None
        copied_report = super(AccountTaxReport, self).copy(default=copy_default) #This copies the report without its lines

        lines_map = {} # maps original lines to their copies (using ids)
        for line in self.get_lines_in_hierarchy():
            copy = line.copy({'parent_id': lines_map.get(line.parent_id.id, None), 'report_id': copied_report.id})
            lines_map[line.id] = copy.id

        return copied_report

    def get_lines_in_hierarchy(self):
        """ Returns an interator to the lines of this tax report, were parent lines
        ar all directly followed by their children.
        """
        self.ensure_one()
        lines_to_treat = list(self.line_ids.filtered(lambda x: not x.parent_id)) # Used as a stack, whose index 0 is the top
        while lines_to_treat:
            to_yield = lines_to_treat[0]
            lines_to_treat = list(to_yield.children_line_ids) + lines_to_treat[1:]
            yield to_yield

    def get_checks_to_perform(self, amounts, carried_over):
        """ To override in localizations
        If value is a float, it will be formatted with format_value
        The line is not displayed if it is falsy (0, 0.0, False, ...)
        :param amounts: the mapping dictionary between codes and values
        :param carried_over: the mapping dictionary between codes and whether they are carried over
        :return: iterable of tuple (name, value)
        """
        self.ensure_one()
        return []

    def validate_country_id(self):
        for record in self:
            if any(line.tag_ids.mapped('country_id') != record.country_id for line in record.line_ids):
                raise ValidationError(_("The tags associated with tax report line objects should all have the same country set as the tax report containing these lines."))


class AccountTaxReportLine(models.Model):
    _name = "account.tax.report.line"
    _description = 'Account Tax Report Line'
    _order = 'sequence, id'
    _parent_store = True

    name = fields.Char(string="Name", required=True, help="Complete name for this report line, to be used in report.")
    tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', relation='account_tax_report_line_tags_rel', help="Tax tags populating this line")
    report_action_id = fields.Many2one(string="Report Action", comodel_name='ir.actions.act_window', help="The optional action to call when clicking on this line in accounting reports.")
    children_line_ids = fields.One2many(string="Children Lines", comodel_name='account.tax.report.line', inverse_name='parent_id', help="Lines that should be rendered as children of this one")
    parent_id = fields.Many2one(string="Parent Line", comodel_name='account.tax.report.line')
    sequence = fields.Integer(string='Sequence', required=True,
        help="Sequence determining the order of the lines in the report (smaller ones come first). This order is applied locally per section (so, children of the same line are always rendered one after the other).")
    parent_path = fields.Char(index=True)
    report_id = fields.Many2one(string="Tax Report", required=True, comodel_name='account.tax.report', ondelete='cascade', help="The parent tax report of this line")

    # helper to create tags (positive and negative) on report line creation
    tag_name = fields.Char(string="Tag Name", help="Short name for the tax grid corresponding to this report line. Leave empty if this report line should not correspond to any such grid.")

    # fields used in specific localization reports, where a report line isn't simply the given by the sum of account.move.line with selected tags
    code = fields.Char(string="Code", help="Optional unique code to refer to this line in total formulas")
    formula = fields.Char(string="Formula", help="Python expression used to compute the value of a total line. This field is mutually exclusive with tag_name, setting it turns the line to a total line. Tax report line codes can be used as variables in this expression to refer to the balance of the corresponding lines in the report. A formula cannot refer to another line using a formula.")

    # fields used to carry over amounts between periods

    # The selection should be filled in localizations using the system
    carry_over_condition_method = fields.Selection(
        selection=[
            ('no_negative_amount_carry_over_condition', 'No negative amount'),
            ('always_carry_over_and_set_to_0', 'Always carry over and set to 0'),
        ],
        string="Method",
        help="The method used to determine if this line should be carried over."
    )
    carry_over_destination_line_id = fields.Many2one(
        string="Destination",
        comodel_name="account.tax.report.line",
        domain="[('report_id', '=', report_id)]",
        help="The line to which the value of this line will be carried over to if needed."
             " If left empty the line will carry over to itself."
    )
    carryover_line_ids = fields.One2many(
        string="Carryover lines",
        comodel_name='account.tax.carryover.line',
        inverse_name='tax_report_line_id',
    )
    is_carryover_persistent = fields.Boolean(
        string="Persistent",
        help="Defines how this report line creates carry over lines when performing tax closing. "
             "If true, the amounts carried over will always be added on top of each other: "
             "for example, a report line with a balance of 10 with an existing carryover of 50 "
             "will add an additional 10 to it when doing the closing, making a total carryover of 60. "
             "If false, the total carried over amount will be forced to the total of this report line: "
             "a report line with a balance of 10 with an existing carryover of 50 will create a new "
             "carryover line of -40, so that the total carryover becomes 10.",
        default=True,
    )
    is_carryover_used_in_balance = fields.Boolean(
        string="Used in line balance",
        help="If set, the carryover amount for this line will be used when calculating its balance in the report. "
             "This means that the carryover could affect other lines if they are using this one in their computation."
    )

    @api.model
    def create(self, vals):
        # Manage tags
        tag_name = vals.get('tag_name', '')
        if tag_name and vals.get('report_id'):
            report = self.env['account.tax.report'].browse(vals['report_id'])
            country = report.country_id

            existing_tags = self.env['account.account.tag']._get_tax_tags(tag_name, country.id)

            if len(existing_tags) < 2:
                # We create new one(s)
                # We can have only one tag in case we archived it and deleted its unused complement sign
                vals['tag_ids'] = self._get_tags_create_vals(tag_name, country.id, existing_tag=existing_tags)
            else:
                # We connect the new report line to the already existing tags
                vals['tag_ids'] = [(6, 0, existing_tags.ids)]

        return super(AccountTaxReportLine, self).create(vals)

    @api.model
    def _get_tags_create_vals(self, tag_name, country_id, existing_tag=None):
        """
            We create the plus and minus tags with tag_name.
            In case there is an existing_tag (which can happen if we deleted its unused complement sign)
            we only recreate the missing sign.
        """
        minus_tag_vals = {
          'name': '-' + tag_name,
          'applicability': 'taxes',
          'tax_negate': True,
          'country_id': country_id,
        }
        plus_tag_vals = {
          'name': '+' + tag_name,
          'applicability': 'taxes',
          'tax_negate': False,
          'country_id': country_id,
        }
        res = []
        if not existing_tag or not existing_tag.tax_negate:
            res.append((0, 0, minus_tag_vals))
        if not existing_tag or existing_tag.tax_negate:
            res.append((0, 0, plus_tag_vals))
        return res

    def write(self, vals):
        # If tag_name was set, but not tag_ids, we postpone the write of
        # tag_name, and perform it only after having generated/retrieved the tags.
        # Otherwise, tag_name and tags' name would not match, breaking
        # _validate_tags constaint.
        postponed_vals = {}

        if 'tag_name' in vals and 'tag_ids' not in vals:
            postponed_vals = {'tag_name': vals.pop('tag_name')}
            tag_name_postponed = postponed_vals['tag_name']
            # if tag_name is posponed then we also postpone formula to avoid
            # breaking _validate_formula constraint
            if 'formula' in vals:
                postponed_vals['formula'] = vals.pop('formula')

        rslt = super(AccountTaxReportLine, self).write(vals)

        if postponed_vals:
            # If tag_name modification has been postponed,
            # we need to search for existing tags corresponding to the new tag name
            # (or create them if they don't exist yet) and assign them to the records

            records_by_country = {}
            for record in self.filtered(lambda x: x.tag_name != tag_name_postponed):
                records_by_country[record.report_id.country_id.id] = records_by_country.get(record.report_id.country_id.id, self.env['account.tax.report.line']) + record

            for country_id, records in records_by_country.items():
                if tag_name_postponed:
                    record_tag_names = records.mapped('tag_name')
                    if len(record_tag_names) == 1 and record_tag_names[0]:
                        # If all the records already have the same tag_name before writing,
                        # we simply want to change the name of the existing tags
                        to_update = records.mapped('tag_ids.tax_report_line_ids')
                        tags_to_update = to_update.mapped('tag_ids')
                        minus_child_tags = tags_to_update.filtered(lambda x: x.tax_negate)
                        minus_child_tags.write({'name': '-' + tag_name_postponed})
                        plus_child_tags = tags_to_update.filtered(lambda x: not x.tax_negate)
                        plus_child_tags.write({'name': '+' + tag_name_postponed})
                        super(AccountTaxReportLine, to_update).write(postponed_vals)

                    else:
                        existing_tags = self.env['account.account.tag']._get_tax_tags(tag_name_postponed, country_id)
                        records_to_link = records
                        tags_to_remove = self.env['account.account.tag']

                        if len(existing_tags) < 2 and records_to_link:
                            # If the tag does not exist yet (or if we only have one of the two +/-),
                            # we first create it by linking it to the first report line of the record set
                            first_record = records_to_link[0]
                            tags_to_remove += first_record.tag_ids
                            first_record.write({**postponed_vals, 'tag_ids': [(5, 0, 0)] + self._get_tags_create_vals(tag_name_postponed, country_id, existing_tag=existing_tags)})
                            existing_tags = first_record.tag_ids
                            records_to_link -= first_record

                        # All the lines sharing their tags must always be synchronized,
                        tags_to_remove += records_to_link.mapped('tag_ids')
                        records_to_link = tags_to_remove.mapped('tax_report_line_ids')
                        tags_to_remove.mapped('tax_report_line_ids')._remove_tags_used_only_by_self()
                        records_to_link.write({**postponed_vals, 'tag_ids': [(2, tag.id) for tag in tags_to_remove] + [(6, 0, existing_tags.ids)]})

                else:
                    # tag_name was set empty, so we remove the tags on current lines
                    # If some tags are still referenced by other report lines,
                    # we keep them ; else, we delete them from DB
                    line_tags = records.mapped('tag_ids')
                    other_lines_same_tag = line_tags.mapped('tax_report_line_ids').filtered(lambda x: x not in records)
                    if not other_lines_same_tag:
                        self._delete_tags_from_taxes(line_tags.ids)
                    orm_cmd_code = other_lines_same_tag and 3 or 2
                    records.write({**postponed_vals, 'tag_ids': [(orm_cmd_code, tag.id) for tag in line_tags]})

        return rslt

    def unlink(self):
        self._remove_tags_used_only_by_self()
        children = self.mapped('children_line_ids')
        if children:
            children.unlink()
        return super(AccountTaxReportLine, self).unlink()

    def _remove_tags_used_only_by_self(self):
        """ Deletes and removes from taxes and move lines all the
        tags from the provided tax report lines that are not linked
        to any other tax report lines nor move lines.
        The tags that are used by at least one move line will be archived instead, to avoid loosing history.
        """
        all_tags = self.mapped('tag_ids')
        tags_to_unlink = all_tags.filtered(lambda x: not (x.tax_report_line_ids - self))
        self.write({'tag_ids': [(3, tag.id, 0) for tag in tags_to_unlink]})

        for tag in tags_to_unlink:
            aml_using_tags = self.env['account.move.line'].sudo().search([('tax_tag_ids', 'in', tag.id)], limit=1)
            # if the tag is still referenced in move lines we archive the tag, else we delete it.
            if aml_using_tags:
                rep_lines_with_archived_tags = self.env['account.tax.repartition.line'].sudo().search([('tag_ids', 'in', tag.id)])
                rep_lines_with_archived_tags.write({'tag_ids': [(3, tag.id)]})
                tag.active = False
            else:
                self._delete_tags_from_taxes([tag.id])

    @api.model
    def _delete_tags_from_taxes(self, tag_ids_to_delete):
        """ Based on a list of tag ids, removes them first from the
        repartition lines they are linked to, then deletes them
        from the account move lines, and finally unlink them.
        """
        if not tag_ids_to_delete:
            # Nothing to do, then!
            return

        self.env.cr.execute("""
            delete from account_account_tag_account_tax_repartition_line_rel
            where account_account_tag_id in %(tag_ids_to_delete)s;

            delete from account_account_tag_account_move_line_rel
            where account_account_tag_id in %(tag_ids_to_delete)s;
        """, {'tag_ids_to_delete': tuple(tag_ids_to_delete)})

        self.env['account.move.line'].invalidate_cache(fnames=['tax_tag_ids'])
        self.env['account.tax.repartition.line'].invalidate_cache(fnames=['tag_ids'])

        self.env['account.account.tag'].browse(tag_ids_to_delete).unlink()

    @api.constrains('formula', 'tag_name')
    def _validate_formula(self):
        for record in self:
            if record.formula and record.tag_name:
                raise ValidationError(_("Tag name and formula are mutually exclusive, they should not be set together on the same tax report line."))

    @api.constrains('tag_name', 'tag_ids')
    def _validate_tags(self):
        for record in self.filtered(lambda x: x.tag_ids):
            neg_tags = record.tag_ids.filtered(lambda x: x.tax_negate)
            pos_tags = record.tag_ids.filtered(lambda x: not x.tax_negate)

            if (len(neg_tags) > 1 or len(pos_tags) > 1):
                raise ValidationError(_("If tags are defined for a tax report line, only two are allowed on it: a positive and/or a negative one."))

            if (neg_tags and neg_tags.name != '-'+record.tag_name) or (pos_tags and pos_tags.name != '+'+record.tag_name):
                raise ValidationError(_("The tags linked to a tax report line should always match its tag name."))

    def action_view_carryover_lines(self, options):
        ''' Action when clicking on the "View carryover lines" in the carryover info popup.
        Takes into account the report options, to get the correct lines depending on the current
        company/companies.

        :return:    An action showing the account.tax.carryover.lines for the current tax report line.
        '''
        self.ensure_one()

        target = self._get_carryover_destination_line(options)
        domain = target._get_carryover_lines_domain(options)
        carryover_lines = self.env['account.tax.carryover.line'].search(domain)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Carryover Lines For %s', target.name),
            'res_model': 'account.tax.carryover.line',
            'view_type': 'list',
            'view_mode': 'list',
            'views': [[self.env.ref('account.account_tax_carryover_line_tree').id, 'list'],
                      [False, 'form']],
            'domain': [('id', 'in', carryover_lines.ids)],
        }

    def _get_carryover_bounds(self, options, line_amount, carried_over_amount):
        """
        Check if the line will be carried over, by checking the condition method set on the line.
        Do not override this method, but instead set your condition methods on each lines.
        :param options: The options of the reports
        :param line_amount: The amount on the line
        :param carried_over_amount: The amount carried over for this line
        :return: A tuple containing the lower and upper bounds from which the line will be carried over.
        E.g. (0, 42) : Lines which value is below 0 or above 42 will be carried over.
        E.g. (0, None) : Only lines which value is below 0 will be carried over.
        E.g. None : This line will never be carried over.
        """
        self.ensure_one()
        # Carry over is disabled by default, but if there is a carry over condition  method on the line we are
        # calling it first. That way we can have a default carryover condition for the whole report (carryover_bounds)
        # and specialized condition for specific lines if needed
        if self.carry_over_condition_method:
            condition_method = getattr(self, self.carry_over_condition_method, False)
            if condition_method:
                return condition_method(options, line_amount, carried_over_amount)

        return None

    def _get_carryover_lines_domain(self, options):
        """
        :param options: The report options
        :return: The domain that can be used to search for carryover lines for this tax report line.
        Using this domain instead of directly accessing the lines ensure that we only pick the ones related to the
        companies affecting the tax report.
        """
        self.ensure_one()
        domain = [('tax_report_line_id', '=', self.id)]

        if options.get('multi_company'):
            company_ids = [company['id'] for company in options['multi_company']]
            domain = expression.AND([domain, [('company_id', 'in', company_ids)]])
        else:
            domain = expression.AND([domain, [('company_id', '=', self.env.company.id)]])

        return domain

    def no_negative_amount_carry_over_condition(self, options, line_amount, carried_over_amount):
        # The bounds are (0, None).
        # Lines below 0 will be set to 0 and reduce the balance of the carryover.
        # Lines above 0 will never be carried over
        return (0, None)

    def always_carry_over_and_set_to_0(self, options, line_amount, carried_over_amount):
        # The bounds are (0, 0).
        # Lines below 0 will be set to 0 and reduce the balance of the carryover.
        # Lines above 0 will be set to 0 and increase the balance of the carryover.
        return (0, 0)

    def _get_carryover_destination_line(self, options):
        """
        Return the destination line for the carryover for this tax report line.
        :param options: The options of the tax report.
        :return: The line on which we'll carryover this tax report line when closing the tax period.
        """
        self.ensure_one()
        return self.carry_over_destination_line_id or self
