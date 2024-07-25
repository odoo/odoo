# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.tools import OrderedSet


class MrpBomLine(models.Model):
    _name = 'mrp.bom.line'
    _order = "sequence, id"
    _rec_name = "product_id"
    _description = 'Bill of Material Line'
    _check_company_auto = True

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    product_id = fields.Many2one('product.product', 'Product Variant', compute='_compute_product_id', inverse='_inverse_product_id', store=True, check_company=True, copy=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product', compute='_compute_product_tmpl_id', store=True, index=True, readonly=False)
    company_id = fields.Many2one(
        related='bom_id.company_id', store=True, index=True, readonly=True)
    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        default=_get_default_product_uom_id,
        required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control", domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    sequence = fields.Integer(
        'Sequence', default=1,
        help="Gives the sequence order when displaying.")
    bom_id = fields.Many2one(
        'mrp.bom', 'Parent BoM',
        index=True, ondelete='cascade', required=True)
    parent_product_tmpl_id = fields.Many2one('product.template', 'Parent Product Template', related='bom_id.product_tmpl_id')
    # Stores the possible attribute values of the bom product template
    possible_bom_product_template_attribute_value_ids = fields.Many2many(related='bom_id.possible_product_template_attribute_value_ids', string="Possible Bom Product Template Attribute Value")
    bom_product_template_attribute_value_ids = fields.Many2many(
        'product.template.attribute.value', string="Apply on Variants", ondelete='restrict',
        domain="[('id', 'in', possible_bom_product_template_attribute_value_ids)]",
        help="BOM Product Variants needed to apply this line.")
    possible_product_template_attribute_value_ids = fields.Many2many(
        'product.template.attribute.value',
        'mrp_bom_line_product_template_attribute_possible_value_rel',
        'bom_line_id', 'product_template_attribute_value_id',
        compute='_compute_possible_product_template_attribute_value_ids')
    # Stores the selected attribute values of the component product template
    selected_product_template_attribute_value_ids = fields.Many2many(
        'product.template.attribute.value',
        'mrp_bom_line_product_template_attribute_selected_value_rel',
        'bom_line_id', 'product_template_attribute_value_id',
        string="Product Attribute", store=True, ondelete='restrict',
        readonly=False,
        compute="_compute_selected_attributes",
        domain="[('id', 'in', possible_product_template_attribute_value_ids)]")
    allowed_operation_ids = fields.One2many('mrp.routing.workcenter', related='bom_id.operation_ids')
    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Consumed in Operation', check_company=True,
        domain="[('id', 'in', allowed_operation_ids)]",
        help="The operation where the components are consumed, or the finished products created.")
    child_bom_id = fields.Many2one(
        'mrp.bom', 'Sub BoM', compute='_compute_child_bom_id')
    child_line_ids = fields.One2many(
        'mrp.bom.line', string="BOM lines of the referred bom",
        compute='_compute_child_line_ids')
    attachments_count = fields.Integer('Attachments Count', compute='_compute_attachments_count')
    tracking = fields.Selection(related='product_id.tracking')
    manual_consumption = fields.Boolean(
        'Manual Consumption', default=False,
        readonly=False, store=True, copy=True,
        help="When activated, then the registration of consumption for that component is recorded manually exclusively.\n"
             "If not activated, and any of the components consumption is edited manually on the manufacturing order, Odoo assumes manual consumption also.")

    _sql_constraints = [
        ('bom_qty_zero', 'CHECK (product_qty>=0)', 'All product quantities must be greater or equal to 0.\n'
            'Lines with 0 quantities can be used as optional lines. \n'
            'You should install the mrp_byproduct module if you want to manage extra products on BoMs!'),
    ]

    @api.depends('product_id')
    def _compute_product_tmpl_id(self):
        for line in self:
            line.product_tmpl_id = line.product_id.product_tmpl_id if line.product_id else line.product_tmpl_id

    @api.depends('product_id')
    def _compute_selected_attributes(self):
        for line in self:
            line.selected_product_template_attribute_value_ids = line.product_id.product_template_attribute_value_ids

    @api.depends('product_tmpl_id')
    def _compute_possible_product_template_attribute_value_ids(self):
        for line in self:
            line.possible_product_template_attribute_value_ids = line.product_tmpl_id\
                .valid_product_template_attribute_line_ids._without_no_variant_attributes()\
                .product_template_value_ids._only_active()

    @api.depends('product_tmpl_id', 'selected_product_template_attribute_value_ids')
    def _compute_product_id(self):
        for line in self:
            if line.product_id and line.product_tmpl_id != line.product_id.product_tmpl_id:
                line.product_id = None
            else:
                product = self.env['product.product'].search([
                    '&', ('product_tmpl_id', '=', line.product_tmpl_id.id),
                    ("product_template_variant_value_ids", 'in', line.selected_product_template_attribute_value_ids.ids)])
                line.product_id = product if product and len(product) == 1 else None

    def _inverse_product_id(self):
        pass

    @api.depends('product_id', 'bom_id')
    def _compute_child_bom_id(self):
        products = self.product_id
        bom_by_product = self.env['mrp.bom']._bom_find(products)
        for line in self:
            if not line.product_id:
                line.child_bom_id = False
            else:
                line.child_bom_id = bom_by_product.get(line.product_id, False)

    @api.depends('product_id')
    def _compute_attachments_count(self):
        for line in self:
            product_ids = line._get_attachment_product_ids()
            nbr_attach = self.env['product.document'].search_count([
                '&', '&', ('attached_on_mrp', '=', 'bom'), ('active', '=', 't'),
                '|',
                '&', ('res_model', '=', 'product.product'), ('res_id', 'in', product_ids),
                '&', ('res_model', '=', 'product.template'), ('res_id', '=', line.product_tmpl_id.id)])
            line.attachments_count = nbr_attach

    @api.depends('child_bom_id')
    def _compute_child_line_ids(self):
        """ If the BOM line refers to a BOM, return the ids of the child BOM lines """
        for line in self:
            line.child_line_ids = line.child_bom_id.bom_line_ids.ids or False

    @api.onchange('product_uom_id')
    def onchange_product_uom_id(self):
        res = {}
        if not self.product_uom_id or not self.product_id:
            return res
        if self.product_uom_id.category_id != self.product_id.uom_id.category_id:
            self.product_uom_id = self.product_id.uom_id.id
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
        return res

    @api.onchange('product_id', 'product_tmpl_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
        elif self.product_tmpl_id:
            self.product_uom_id = self.product_tmpl_id.uom_id.id

    @api.model_create_multi
    def create(self, vals_list):

        def ids_from_values(name):
            return_ids = []
            for orm_command in values.get(name, []):
                if orm_command[0] == Command.SET:
                    return_ids += orm_command[2]
                else:
                    return_ids.append(orm_command[1])
            return return_ids

        for values in vals_list:
            if 'product_id' in values and 'product_uom_id' not in values and "product_tmpl_id" not in values:
                values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
            if 'product_id' in values and values.get('product_id'):
                continue

            # Prepare all values to check the attribute values
            product_tmpl_id = self.env["product.template"].browse(values["product_tmpl_id"])
            if not product_tmpl_id:
                raise UserError(_('You need to specify a product_tmpl_id'))

            bom_id = self.env["mrp.bom"].browse(values.get("bom_id"))
            possible_bom_ptavs = bom_id.possible_product_template_attribute_value_ids if bom_id else False
            possible_ptavs = product_tmpl_id.valid_product_template_attribute_line_ids\
                ._without_no_variant_attributes().product_template_value_ids._only_active()

            bom_ptav_ids = ids_from_values('bom_product_template_attribute_value_ids')
            bom_ptavs = self.env["product.template.attribute.value"].browse(bom_ptav_ids)

            selected_ptavs_ids = ids_from_values('selected_product_template_attribute_value_ids')
            selected_ptavs = self.env["product.template.attribute.value"].browse(selected_ptavs_ids)

            self._check_attribute_values(product_tmpl_id, bom_id,
                                         possible_bom_ptavs, bom_ptavs,
                                         possible_ptavs, selected_ptavs)

        return super().create(vals_list)

    def write(self, vals_list):
        res = super().write(vals_list)
        self._check_attribute_values(self.product_tmpl_id, self.bom_id,
            self.possible_bom_product_template_attribute_value_ids,
            self.bom_product_template_attribute_value_ids,
            self.possible_product_template_attribute_value_ids,
            self.selected_product_template_attribute_value_ids
        )
        if self and not self.product_id and not self.product_tmpl_id:
            raise UserError(_('You need to specify a product_tmpl_id'))
        return res

    def _skip_bom_line(self, product, never_attribute_values=False):
        """ Control if a BoM line should be produced, can be inherited to add custom control.
            cases:
                - no_variant:
                    1. attribute present on the line
                        => need to be at least one attribute value matching between the one passed as args and the ones one the line
                    2. attribute not present on the line
                        => valid if the line has no attribute value selected for that attribute
                - always and dynamic: match_all_variant_values()
        """
        self.ensure_one()
        if product._name == 'product.template':
            return False

        # attributes create_variant 'always' and 'dynamic'
        other_attribute_valid = product._match_all_variant_values(self.bom_product_template_attribute_value_ids.filtered(lambda a: a.attribute_id.create_variant != 'no_variant'))

        # if there are no never attribute values on the bom line => always and dynamic

        if not self.bom_product_template_attribute_value_ids.filtered(lambda a: a.attribute_id.create_variant == 'no_variant'):
            return not other_attribute_valid

        # or if there are never attribute on the line values but no value is passed => impossible to match
        if not never_attribute_values:
            return True

        bom_values_by_attribute = self.bom_product_template_attribute_value_ids.filtered(
                lambda a: a.attribute_id.create_variant == 'no_variant'
            ).grouped('attribute_id')

        never_values_by_attribute = never_attribute_values.grouped('attribute_id')

        for a_id, a_values in bom_values_by_attribute.items():
            if any(a.id in never_values_by_attribute[a_id].ids for a in a_values):
                continue
            return True
        return not other_attribute_valid

    def action_see_attachments(self):
        product_ids = self._get_attachment_product_ids()
        domain = [
            '&', ('attached_on_mrp', '=', 'bom'),
            '|',
            '&', ('res_model', '=', 'product.product'), ('res_id', 'in', product_ids),
            '&', ('res_model', '=', 'product.template'), ('res_id', '=', self.product_tmpl_id.id)]
        attachments = self.env['product.document'].search(domain)
        nbr_product_attach = len(attachments.filtered(lambda a: a.res_model == 'product.product'))
        nbr_template_attach = len(attachments.filtered(lambda a: a.res_model == 'product.template'))
        context = {'default_res_model': 'product.product' if self.product_id else 'product.template',
            'default_res_id': self.product_id.id or self.product_tmpl_id.id,
            'default_company_id': self.company_id.id,
            'attached_on_bom': True,
            'search_default_context_variant': not (nbr_product_attach == 0 and nbr_template_attach > 0) if self.env.user.has_group('product.group_product_variant') and self.product_id else False
        }

        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'product.document',
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'target': 'current',
            'help': _('''<p class="o_view_nocontent_smiling_face">
                        Upload files to your product
                    </p><p>
                        Use this feature to store any files, like drawings or specifications.
                    </p>'''),
            'limit': 80,
            'context': context,
            'search_view_id': self.env.ref('product.product_document_search').ids
        }

    def _get_child_bom_by_product(self, product):
        self.ensure_one()
        return self.env['mrp.bom']._bom_find(product).get(product, False)

    def _get_attachment_product_ids(self):
        if self.product_id:
            return [self.product_id.id]
        product_ids = set()
        for bpp in self.env['product.product'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)]):
            [product_ids.add(p.id) for p in self.get_product_variant(bpp, ignore_bom_product=True)]
        return list(product_ids)

    def _get_initial_valid_attribute_values(self, product):
        """
            Compute the attribute line values that are initially valid.
            Selected values are valid if:
                - There is only one value selected for that attribute
                - There is not such attribute on the product
            returns the values and the attributes validated
        """
        ptav = self.env['product.template.attribute.value']
        attributes_validated = self.env['product.attribute']
        sptav_grouped_by_attribute = self.selected_product_template_attribute_value_ids.grouped('attribute_id')

        for attribute, sptav in sptav_grouped_by_attribute.items():
            if len(sptav) == 1 or sptav.attribute_id not in product.product_template_attribute_value_ids.attribute_id:
                ptav |= sptav
                attributes_validated |= attribute

        return ptav, attributes_validated

    def _get_valid_attributes_values_from_selected_bom_product_values(self, product, ptav, common_pa):
        """
            This function checks if there is a product template attribute value that match the following conditions:
                1. The ptav of the BoM product must be present on the bom line
                2. The component must have the same attribute
                3. If 1 and 2 are True, a ptav on the component has to be the same than the ptav of the BoM product

            Appends to ptav the newly validated product template attribute value and remove the validted attribute from the common_pa.
            Params: ptav: the recordset of product template attribute values already selected on which new valid values will be added
                    common_pa: the common attributes of the product and the bom line product template
        """
        pptav_grouped_by_attribute = self.possible_product_template_attribute_value_ids.grouped('attribute_id')
        for bptav in self.bom_product_template_attribute_value_ids:
            if bptav not in product.product_template_attribute_value_ids or bptav.attribute_id not in common_pa:
                continue
            common_pa = common_pa - bptav.attribute_id
            pptav = pptav_grouped_by_attribute.get(bptav.attribute_id)\
                .filtered(lambda v: v.product_attribute_value_id == bptav.product_attribute_value_id)

            if not pptav:
                raise UserError(_("Missing attribute value for %(att_name)s on the component %(tmpl_name)s",
                                    att_name=bptav.attribute_id.name,
                                    tmpl_name=self.product_tmpl_id.name))
            ptav |= pptav
        return ptav, common_pa

    def _get_valid_attribute_values_from_bom_line_product(self, talv, common_pa, compo_additional_pa):
        """
            This function validates the ptavs on the BoM component that don't have an equivalent attribute on the BoM product
            The ptavs are validated if there is only one value selected per attribute
        """
        attributes_to_remove = self.env['product.attribute']
        ptavs_grouped_by_attribute = self.selected_product_template_attribute_value_ids.grouped('attribute_id')
        for pa in compo_additional_pa:
            ptavs = ptavs_grouped_by_attribute.get(pa)
            if not ptavs:
                raise UserError(_("Missing attribute value for %(pal)s on the component %(tmpl_name)s",
                    pal=pa.name,
                    tmpl_name=self.product_tmpl_id.name)
                )
            if len(ptavs) > 1:
                raise UserError(_("Too many attribute values for %(pal)s on the component %(tmpl_name)s",
                                    pal=pa.name, tmpl_name=self.product_tmpl_id.name))
            talv |= ptavs
            attributes_to_remove |= pa
        return talv, common_pa - attributes_to_remove

    def _get_valid_attribute_values_from_common_attributes(self, talv, common_pa, product, ignore_bom_product):
        """
            This function finds a valid product template attribute value for each of the common attributes.
        """
        prod_value_grouped_by_attribute = product.product_template_attribute_value_ids.grouped('attribute_id')
        pptav_grouped_by_attribute_value = self.possible_product_template_attribute_value_ids.grouped('product_attribute_value_id')
        sptav_grouped_by_attribute = self.selected_product_template_attribute_value_ids.grouped('product_attribute_value_id')

        for pa in common_pa:
            prod_value = prod_value_grouped_by_attribute.get(pa)
            ptav = pptav_grouped_by_attribute_value.get(prod_value.product_attribute_value_id)
            if ignore_bom_product:
                ptav = ptav.filtered(
                    lambda ppav: ppav in self.selected_product_template_attribute_value_ids if sptav_grouped_by_attribute.get(pa) else True
                )
            if ptav:
                talv |= ptav
            else:
                return False
        return talv

    def _attribute_no_bom_product_check(self, prod):
        """
            Returns True if the product can match the BoM line selected attributes, no matter the main BoM product
            This means that if there are no value for an attribute on selected attributes on the BoM, it will return true for that attribute, no matter the value selected on the product
            If there is one or many selected values on the BoM line, it will return true for all product where the attribute value selected is among thoses selected on the line.
        """
        selected_grouped_by_attribute = self.selected_product_template_attribute_value_ids.grouped('attribute_id')
        for ptav in prod.product_template_attribute_value_ids:
            selected_ptavs = selected_grouped_by_attribute.get(ptav.attribute_id)
            if not selected_ptavs:
                continue
            if ptav.id not in selected_ptavs.ids:
                return False
        return True

    def _attribute_minimal_check(self, prod):
        """
            Returns True if the product can match the BoM line selected attributes, no matter the main BoM product
            This means that if there are no value for an attribute on selected attributes on the BoM, it will return true for that attribute, no matter the value selected on the product
            If there is one or many selected values on the BoM line, it will return true for all product where the attribute value selected is among thoses selected on the line.
        """
        for ptav in prod.product_template_attribute_value_ids:
            selected_ptavs = self.selected_product_template_attribute_value_ids.filtered(lambda v: v.attribute_id == ptav.attribute_id)
            if not selected_ptavs:
                continue
            if ptav.id not in selected_ptavs.ids:
                return False
        return True

    def get_product_variant(self, product, ignore_bom_product=False):
        """
            This function return the product variant (the component on the BoM line) to use with the product passed in params

            We need to match the attribute values with the product attribute values if possible.
            The product variant (and thus the attributes values) is chosen by following theses rules:

            If there is a product.product defined on the BoM line, all the following logic is bypassed and we return the product.product
            If an attribute value is defined on the line, no need to recompute it

            There are multiple options for each attribute:

                1: There is the same attribute on the product and the component
                    a: The value present on the BoM product is present on the compo => match
                    b: There is a value on the compo not present on the BoM product => never match
                    c: The value on the BoM product is not present on the compo => never match except if the attribute value is set
                2: There is an attribute that is present on the BoM product but not on the compo
                    The match is done on all other attributes, so the value on that specific BoM product attribute does not matter
                3: There is an attribute that is present on the compo but not on the BoM product
                    Need to specify the attribute value on the component or throw an error

            Params:
                product (product.product): The product_product of the BoM.
                ignore_bom_product (boolean): If True, the function will return all products of the line that satisfy the minimal
                    requirements of the line, disregarding the BoM product.
        """

        if self.product_id:
            return self.product_id

        # initial validation
        validated_ptav, attributes_validated = self._get_initial_valid_attribute_values(product)

        component_pa = self.possible_product_template_attribute_value_ids.attribute_id - attributes_validated
        product_pa = product.product_template_attribute_value_ids.attribute_id - attributes_validated
        common_pa = (component_pa & product_pa)
        compo_additional_pa = component_pa.filtered(lambda cpa: cpa not in product_pa)

        # Fill the validated_ptav while removing the attributes already checked
        validated_ptav, common_pa = self._get_valid_attributes_values_from_selected_bom_product_values(product, validated_ptav, common_pa)
        validated_ptav, common_pa = self._get_valid_attribute_values_from_bom_line_product(validated_ptav, common_pa, compo_additional_pa)
        validated_ptav = self._get_valid_attribute_values_from_common_attributes(validated_ptav, common_pa, product, ignore_bom_product)

        if isinstance(validated_ptav, bool) and not validated_ptav:
            return False

        possible_products = self.env['product.product'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)])
        if ignore_bom_product:
            product_match = [p for p in possible_products if self._attribute_no_bom_product_check(p)]
        else:
            product_match = [p for p in possible_products if OrderedSet(p.product_template_attribute_value_ids.ids) == OrderedSet(validated_ptav.ids)]

        # The only option is a uncreated dynamic variant
        if not product_match and any(talv.create_variant == "dynamic" for talv in validated_ptav.attribute_id):
            return self.product_tmpl_id._create_product_variant(validated_ptav)

        if ignore_bom_product:
            return product_match

        return product_match[0] if len(product_match) == 1 else False  # not possible to find multiple variants

    def _check_attribute_values(self, product_tmpl_id, bom_id, possible_bom_ptavs, bom_ptavs, possible_ptavs, selected_ptavs):
        """
        Check the validity of attribute values for a given product template (on the BoM line) regarding the BoM.

        Parameters:
            product_tmpl_id (product.template): The product template of the BoM line.
            bom_id (mrp.bom): The BoM.
            possible_bom_ptavs: Recordset of possible product template attribute values for the product of the BoM.
            bom_ptavs: Recordset of product template attribute values related to the BoM and selected on the BoM line.
            possible_ptavs: Recordset of possible product template attribute values for the component of the BoM line.
            selected_ptavs: Recordset of selected product template attribute values for the component of the BoM line.
        """

        # Check validity for multiple attribute values with the same attribute
        self._many_attribute_values_of_same_attribute_validity_check(product_tmpl_id, bom_id,
                                                                        possible_bom_ptavs, bom_ptavs,
                                                                        selected_ptavs)

        common_pa = (possible_ptavs.attribute_id & possible_bom_ptavs.attribute_id).filtered(lambda pal: pal not in selected_ptavs.attribute_id)
        # Check for missing values on common attributes
        for pa in common_pa:
            self._missing_values_common_attribute_check(pa, product_tmpl_id, possible_bom_ptavs, bom_ptavs, possible_ptavs, selected_ptavs)

        # Check for missing values on non common attributes
        missing_pal = possible_ptavs.attribute_id\
            .filtered(lambda cpal: cpal not in bom_id.product_tmpl_id.attribute_line_ids.attribute_id and cpal not in selected_ptavs.attribute_id)
        if missing_pal:
            raise UserError(_("Missing attribute value for %(pal_name)s on the component %(tmpl_name)s",
                pal_name=missing_pal.name if len(missing_pal) == 1 else missing_pal[0].name,
                tmpl_name=product_tmpl_id.name)
            )

    def _many_attribute_values_of_same_attribute_validity_check(self, product_tmpl_id, bom_id, possible_bom_ptavs, bom_ptavs, selected_ptavs):
        """
        Checks the validity of attribute values (selected on the BoM line) having the same attribute.
        Validity check's logic:
            1: if there is a product_id on the BoM =>
                Only one attribute value can be selected for each attribute for the component as no matching is possible
            2: if there is no product_id on the BoM =>
                a: if all the values selected on the BoM line are also present on the BoM product =>
                    The attributes are valid
                b: if the values on the component can be associated to values on the product and if there is no value selected for an attribute that has dupplicated values on the component =>
                    The attributes are valid
                c: impossible to match

        Returns nothing if all checks are valid, or raise an UserError if too many attribute values are selected for the component/if the attribute values
            cannot be matched between the BoM product and the BoM component.
        """

        # Get the attribute that have multiple values selected
        select_pavs_grouped = selected_ptavs.product_attribute_value_id.grouped("attribute_id")
        attribute_values_duplicate = self.env["product.attribute.value"]
        for spavg in select_pavs_grouped:
            if len(select_pavs_grouped[spavg]) > 1:
                attribute_values_duplicate += select_pavs_grouped[spavg]

        if not attribute_values_duplicate:
            return

        # Only one value is possible for each attribute value if there is a product on the BoM
        if bom_id.product_id:
            raise UserError(_("Too many attribute values for %(attr_name)s on the component %(tmpl_name)s, only one value is allowed",
                attr_name=attribute_values_duplicate[:1].attribute_id.name,
                tmpl_name=product_tmpl_id.name)
            )

        # If there are the exact same product attribute values on the component and the product, then the match is still valid
        if all(e in bom_ptavs.product_attribute_value_id for e in attribute_values_duplicate):
            return

        # The values on the component are valid only if they can be associated to values on the product.
        # This also implies that we need the same attribute values for selected compo attribute values and possible BoM values, with no attribute values selected on the product
        bom_ptavs_grouped_by_attribute = bom_ptavs.grouped('attribute_id')
        valid_values_on_component = (all(e in possible_bom_ptavs.product_attribute_value_id for e in attribute_values_duplicate)
            and not bom_ptavs_grouped_by_attribute.get(attribute_values_duplicate.attribute_id))
        if valid_values_on_component:
            return

        new_attribute_values_duplicate = bom_ptavs.filtered(lambda v: v.attribute_id in attribute_values_duplicate.attribute_id).product_attribute_value_id
        if not new_attribute_values_duplicate:
            raise UserError(_("Too many attribute values for %(attr_name)s on the component %(tmpl_name)s, only one value is allowed",
                attr_name=attribute_values_duplicate[:1].attribute_id.name,
                tmpl_name=product_tmpl_id.name)
            )
        raise UserError(_("Impossible to match attribute value %(av_name)s found for %(a_name)s on the component %(tmpl_name)s",
            av_name=new_attribute_values_duplicate[:1].name,
            a_name=new_attribute_values_duplicate[:1].attribute_id.name,
            tmpl_name=product_tmpl_id.name)
        )

    def _missing_values_common_attribute_check(self, pa, product_tmpl_id, possible_bom_ptavs, bom_ptavs, possible_ptavs, selected_ptavs):
        compo_ptav = possible_ptavs.filtered(lambda v: v.attribute_id == pa)
        bom_product_ptav = possible_bom_ptavs.filtered(lambda v: v.attribute_id == pa)
        bom_selected_ptav = bom_ptavs.filtered(lambda v: v.attribute_id == pa)
        compo_selected_ptav = selected_ptavs.filtered(lambda v: v.attribute_id == pa)
        compo_possible_ptav = possible_ptavs.filtered(lambda v: v.attribute_id == pa)

        # The only safe case is when there are values selected for that attribute on both the bom and component product.
        # The length of the BoM selected attributes value has to be 1 as this is the only case where it does not need matching
        if bom_selected_ptav and compo_selected_ptav and len(bom_selected_ptav) == 1:
            return

        invalid_component_attribute_values = invalid_product_attribute_values = self.env['product.attribute.value']
        # No match possible if attribute value present on the BoM but not on the component
        if any(bsptav not in compo_possible_ptav.product_attribute_value_id for bsptav in bom_selected_ptav.product_attribute_value_id):
            invalid_product_attribute_values = (bom_product_ptav.product_attribute_value_id - compo_ptav.product_attribute_value_id)

        # Check if all values selected on the BoM product can match a possible value on the component
        is_bom_selected_value_correct = bom_selected_ptav and\
            all(e in compo_ptav.mapped('product_attribute_value_id.id') for e in bom_selected_ptav.mapped('product_attribute_value_id.id'))
        if not is_bom_selected_value_correct:
            invalid_component_attribute_values = (bom_product_ptav.product_attribute_value_id - compo_ptav.product_attribute_value_id)

        invalid_attribute_values = (invalid_component_attribute_values + invalid_product_attribute_values)[:1]
        if invalid_attribute_values:
            raise UserError(_("Attribute value '%(av_name)s' could not be matched on the attribute '%(pa_name)s' (component '%(tmpl_name)s')",
                av_name=invalid_attribute_values.name,
                pa_name=pa.name,
                tmpl_name=product_tmpl_id.name)
            )

    # -------------------------------------------------------------------------
    # CATALOG
    # -------------------------------------------------------------------------

    def action_add_from_catalog(self):
        bom = self.env['mrp.bom'].browse(self.env.context.get('order_id'))
        return bom.with_context(child_field='bom_line_ids').action_add_from_catalog()

    def _get_product_catalog_lines_data(self, default=False, **kwargs):
        if self and not default:
            self.product_id.ensure_one()
            return {
                **self[0].bom_id._get_product_price_and_data(self[0].product_id),
                'quantity': sum(
                    self.mapped(
                        lambda line: line.product_uom_id._compute_quantity(
                            qty=line.product_qty,
                            to_unit=line.product_uom_id,
                        )
                    )
                ),
                'readOnly': len(self) > 1,
            }
        return {
            'quantity': 0,
        }