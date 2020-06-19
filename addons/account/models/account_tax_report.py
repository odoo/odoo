# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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

                        if new_tags:
                            tags_to_unlink = line.tag_ids.filtered(lambda x: record == x.mapped('tax_report_line_ids.report_id'))
                            # == instead of in, as we only want tags_to_unlink to contain the tags that are not linked to any other report than the one we're considering
                            line.write({'tag_ids': [(6, 0, new_tags.ids)]})
                            self.env['account.tax.report.line']._delete_tags_from_taxes(tags_to_unlink.ids)

                        elif line.mapped('tag_ids.tax_report_line_ids.report_id').filtered(lambda x: x not in self):
                            line.write({'tag_ids': [(5, 0, 0)] + line._get_tags_create_vals(line.tag_name, vals['country_id'])})
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
        for line in self.line_ids:
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

    def get_checks_to_perform(self, d):
        """ To override in localizations
        If value is a float, it will be formatted with format_value
        The line is not displayed if it is falsy (0, 0.0, False, ...)
        :param d: the mapping dictionay between codes and values
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
    _order = 'sequence'
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

    #helper to create tags (positive and negative) on report line creation
    tag_name = fields.Char(string="Tag Name", help="Short name for the tax grid corresponding to this report line. Leave empty if this report line should not correspond to any such grid.")

    #fields used in specific localization reports, where a report line isn't simply the given by the sum of account.move.line with selected tags
    code = fields.Char(string="Code", help="Optional unique code to refer to this line in total formulas")
    formula = fields.Char(string="Formula", help="Python expression used to compute the value of a total line. This field is mutually exclusive with tag_name, setting it turns the line to a total line. Tax report line codes can be used as variables in this expression to refer to the balance of the corresponding lines in the report. A formula cannot refer to another line using a formula.")

    @api.model
    def create(self, vals):
        # Manage tags
        tag_name = vals.get('tag_name', '')
        if tag_name and vals.get('report_id'):
            report = self.env['account.tax.report'].browse(vals['report_id'])
            country = report.country_id

            existing_tags = self.env['account.account.tag']._get_tax_tags(tag_name, country.id)

            if existing_tags:
                # We connect the new report line to the already existing tags
                vals['tag_ids'] = [(6, 0, existing_tags.ids)]
            else:
                # We create new ones
                vals['tag_ids'] = self._get_tags_create_vals(tag_name, country.id)

        return super(AccountTaxReportLine, self).create(vals)

    @api.model
    def _get_tags_create_vals(self, tag_name, country_id):
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
        return [(0, 0, minus_tag_vals), (0, 0, plus_tag_vals)]

    def write(self, vals):
        tag_name_postponed = None

        # If tag_name was set, but not tag_ids, we postpone the write of
        # tag_name, and perform it only after having generated/retrieved the tags.
        # Otherwise, tag_name and tags' name would not match, breaking
        # _validate_tags constaint.
        postpone_tag_name = 'tag_name' in vals and not 'tag_ids' in vals

        if postpone_tag_name:
            tag_name_postponed = vals.pop('tag_name')

        rslt = super(AccountTaxReportLine, self).write(vals)

        if postpone_tag_name:
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
                        super(AccountTaxReportLine, to_update).write({'tag_name': tag_name_postponed})

                    else:
                        existing_tags = self.env['account.account.tag']._get_tax_tags(tag_name_postponed, country_id)
                        records_to_link = records
                        tags_to_remove = self.env['account.account.tag']

                        if not existing_tags and records_to_link:
                            # If the tag does not exist yet, we first create it by
                            # linking it to the first report line of the record set
                            first_record = records_to_link[0]
                            tags_to_remove += first_record.tag_ids
                            first_record.write({'tag_name': tag_name_postponed, 'tag_ids': [(5, 0, 0)] + self._get_tags_create_vals(tag_name_postponed, country_id)})
                            existing_tags = first_record.tag_ids
                            records_to_link -= first_record

                        # All the lines sharing their tags must always be synchronized,
                        tags_to_remove += records_to_link.mapped('tag_ids')
                        records_to_link = tags_to_remove.mapped('tax_report_line_ids')
                        self._delete_tags_from_taxes(tags_to_remove.ids)
                        records_to_link.write({'tag_name': tag_name_postponed, 'tag_ids': [(2, tag.id) for tag in tags_to_remove] + [(6, 0, existing_tags.ids)]})

                else:
                    # tag_name was set empty, so we remove the tags on current lines
                    # If some tags are still referenced by other report lines,
                    # we keep them ; else, we delete them from DB
                    line_tags = records.mapped('tag_ids')
                    other_lines_same_tag = line_tags.mapped('tax_report_line_ids').filtered(lambda x: x not in records)
                    if not other_lines_same_tag:
                        self._delete_tags_from_taxes(line_tags.ids)
                    orm_cmd_code = other_lines_same_tag and 3 or 2
                    records.write({'tag_name': None, 'tag_ids': [(orm_cmd_code, tag.id) for tag in line_tags]})

        return rslt

    def unlink(self):
        self._delete_tags_from_taxes(self.mapped('tag_ids.id'))
        children = self.mapped('children_line_ids')
        if children:
            children.unlink()
        return super(AccountTaxReportLine, self).unlink()

    @api.model
    def _delete_tags_from_taxes(self, tag_ids_to_delete):
        """ Based on a list of tag ids, removes them first from the
        repartition lines they are linked to, then deletes them
        from the account move lines.
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

            if (len(neg_tags) != 1 or len(pos_tags) != 1):
                raise ValidationError(_("If tags are defined for a tax report line, only two are allowed on it: a positive and a negative one."))

            if neg_tags.name != '-'+record.tag_name or pos_tags.name != '+'+record.tag_name:
                raise ValidationError(_("The tags linked to a tax report line should always match its tag name."))
