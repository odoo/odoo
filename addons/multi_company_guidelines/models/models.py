# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class SharedModel(models.Model):
    """
    Example implementation of a shared model which can be optionally restricted.
    
    Typical use case: product
    """

    _name = "multi_company.shared"
    _description = "Shared Model"

    name = fields.Char(default="Test Shared Record")
    company_id = fields.Many2one("res.company", string="Company", index=True)
    property_field = fields.Char("Company-dependent Field", company_dependent=True)

    def write(self, vals):
        new_company_id = vals.get("company_id")
        if new_company_id and [new_company_id] != self.company_id.ids:
            # check if records specific to this module are using the records
            # in a record that is exclusive to the previous company field's value
            # (and where changing the record's company could potentially block flows)
            # NOTE: depending on the expected size of the table that must be checked,
            # it could be a good idea to be able to directly indicate *which* record
            # is problematic in the error message. This is left at the appreciation
            # of the developper, since it may impact performance and can come with
            # its share of UX problems (e.g. you should not raise when you find the first
            # problematic record but isntead list all of them in the same message
            # to avoid forcing the user to deselect records one by one in their selection)
            self.env.cr.execute(
                """
                SELECT count(*)
                FROM multi_company_line
                WHERE shared_id in (%s) AND
                      company_id != %s
            """,
                (tuple(self.ids), new_company_id),
            )
            prevent_company_change = self.env.cr.fetchone()[0]
            if prevent_company_change:
                raise UserError(
                    _(
                        "The company cannot be changed on the current selection since "
                        "documents from other companies already reference them.\n"
                        "You can either delete all documents that point to the current "
                        "selection or archive the problematic record and recreate it "
                        "for a specific company from scratch."
                    )
                )
        return super().write(vals)


class MainModel(models.Model):
    """Example implementation of a business model holding lines and for which the company is typically required.
    
    This model implements business flows which change its state and potentially trigger creation of records
    in another model as part of its business flow.
    
    Typical use case: sale.order
    """

    _name = "multi_company.main"
    _description = "Main Model"

    name = fields.Char(default="Test Parent Record")
    partner_id = fields.Many2one("res.partner", string="Customer", required=True)
    line_ids = fields.One2many(
        "multi_company.line", "main_id", string="Lines", auto_join=True
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda s: s.env.company.id,
        index=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("posted", "Posted")],
        default="draft",
        required=True,
    )

    def company_consistency_check(self):
        """
        Checks the consistancy of company fields vis-a-vis relational field targets.
        
        This method should be called by *all* business flow methods (validation, etc.) to prevent transmitting
        incorrect data along the flow - it should not be implemented in constraints though.
        
        For perf reaons, you might want to do this check in sql in some cases (although this is not strongly recommended).
        
        This method should be public and raise errors that do not leak data, or private with a public wrapper
        that does not leak data (catch and re-raise with a more generic error msg).
        """
        for record in self:
            errors = []
            # check partners
            if (
                record.partner_id.company_id
                and record.partner_id.company_id != record.company_id
            ):
                errors.append(
                    _(
                        "\n - The customer should either be shared or belong to the company of the document."
                    )
                )
            # in some cases, you might want to disable prefetch here
            # although if you disable the prefetch, extension of this models that extend the company check
            # might have decreased performance since they'll have to re-read their own fields
            # another possibility is to do it in SQL directly
            shared_record_companies = record.line_ids.shared_id.company_id
            if shared_record_companies and shared_record_companies != record.company_id:
                errors.append(
                    _(
                        "\n - Some master data records belong to a different company than the one from the document."
                    )
                )
                # here you could extend the error message to specify the name of records that are not shared and not in
                # the same company to help the user correct the issue more easily
                # do this carefully since it might degrade perfs or might be inconsistent in the UI
                # if you use SQL to fetch non-translated values of translatable fields
            if errors:
                base_msg = _(
                    'There is an inconsistency in the document "%s" which would cause multi-company issues'
                    % (record.name,)
                )
                show_details = self.env.user.has_group(
                    "base.group_user"
                )  # don't leak data to non-internal users
                details_msg = errors if show_details else ""
                print("".join([base_msg] + details_msg))
                raise ValidationError("".join([base_msg] + details_msg))

    def _prepare_next_values(self):
        """
        Prepare a dictionnary of values for a new record in the flow.
        
        You should ensure that force_company is in the context with the company of
        the parent record (for company dependent fields) and that company_id fields (or the
        relationnal field from which the company comes in the case of a stored related field)
        is present in the dictionnary of values!
        """
        self.ensure_one()
        return {
            "name": "Next from main record %s" % self.id,
            "company_id": self.company_id.id,
        }

    def create_next_record(self):
        record = self.with_context(force_company=self.company_id.id)
        vals = record._prepare_next_values()
        return record.env["multi_company.next"].create(vals)

    def _prepare_post_values(self):
        self.ensure_one()
        # get the 'source' object; typically a bit more complex. Think getting
        # the default sales journal of the company...
        magic_source_record = self.env["multi_company.source"].search(
            [("company_id", "=", self.company_id.id)], limit=1
        )
        if not magic_source_record:
            raise UserError(_("There is no source model."))
        return {"source_id": magic_source_record.id}

    def create_post_record(self):
        record = self.with_context(force_company=self.company_id.id)
        vals = record._prepare_post_values()
        return record.env["multi_company.related"].create(vals)

    def action_confirm(self):
        self.company_consistence_check()
        for record in self:
            record.create_next_record()
        self.write({"state": "confirmed"})

    def action_draft(self):
        self.company_consistence_check()
        self.write({"state": "draft"})

    def action_post(self):
        self.company_consistence_check()
        for record in self:
            record.create_post_record()
        self.write({"state": "posted"})


class LineModel(models.Model):
    """Example implementation of a "line" business model.
    
    Hold reference to a parent model, a stored readonly related to its parent and a link to a possibly shared model.
    
    Typical use case: sale.order.line
    """

    _name = "multi_company.line"
    _description = "Line Model"

    name = fields.Char()
    shared_id = fields.Many2one(
        "multi_company.shared", string="Shared Record", required=True, index=True
    )
    main_id = fields.Many2one("multi_company.main", string="Parent", index=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="main_id.company_id",
        readonly=True,
        store=True,
        index=True,
    )

    @api.onchange("shared_id")
    def onchange_shared_id(self):
        for line in self:
            shared_id = line.shared_id.with_context(
                force_company=line.company_id.id or self.env.company.id
            )
            line.name = shared_id.property_field


class NextStepModel(models.Model):
    """
    Example implementation of a followup record created as part of the flow of the main one.
    
    This model can be created both programmatically as part of the business flow of the main model
    or directly by users via the client. In the case of programmatic creation, the company is usually forwarded
    from the main model (although this can depend on use cases) while in the case of creation from scratch
    it comes from the user's default company.
    
    Typical use case: project.task in a service-based sales flow
    """

    _name = "multi_company.next"
    _description = "Follow-up Model"

    name = fields.Char(default="Test Follow-up Record")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda s: s.env.company.id,
        index=True,
    )


class MagicSourceModel(models.Model):
    """
    Example implementation of a record holding the company field for another business model through a related.

    Typical use case: account.journal (account.move gets company as related on journal)
    """

    _name = "multi_company.source"
    _description = "Source Model for Related Company"

    name = fields.Char(default="Test Source Record")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda s: s.env.company.id,
        index=True,
    )


class RelatedMagicModel(models.Model):
    """Example implementation of a followup record for which the company_id field comes as a stored related.
    
    This model can be created both programmatically as part of the business flow of the main model
    or directly by users via the client. In the case of programmatic creation, the company is not forwarded
    from the main model (although this can depend on use cases) while in the case of creation from scratch
    it comes from the user's default company. Note that the related field must be stored (for ir.rules)
    and readonly (to avoid accidentally writing on the source record invisibly, thereby corrupting the db
    and triggering a massive recompute).
    
    Typical use case: account.move (company related on journal)
    """

    _name = "multi_company.related"
    _description = "Related Magic Model"

    name = fields.Char(default="Test Magic Related Record")
    source_id = fields.Many2one(
        "multi_company.source", string="Source Record for Company", required=True
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="source_id.company_id",
        readonly=True,
        store=True,
        index=True,
    )

