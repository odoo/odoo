# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from lxml import etree

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError

# Matches the static registration of a field widget, i.e.
# registry.category("fields").add("widget_name", ...).
FIELD_WIDGET_REGISTRATION_RE = re.compile(
    r"""category\(\s*["']fields["']\s*\)\s*\.\s*add\(\s*["']([\w.]+)["']"""
)


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'pos.load.mixin']

    pos_order_count = fields.Integer(
        compute='_compute_pos_order',
        help="The number of point of sales orders related to this customer",
        groups="point_of_sale.group_pos_user",
    )
    pos_order_ids = fields.One2many('pos.order', 'partner_id', readonly=True)

    @api.model
    def get_views(self, views, options=None):
        # The action context is not part of what the web client sends along
        # with get_views (it only forwards lang and *_view_ref), so the POS
        # partner editor is recognized through the action id the client always
        # passes instead.
        if options and options.get('action_id'):
            action = self.env.ref(
                'point_of_sale.res_partner_action_edit_pos', raise_if_not_found=False
            )
            if action and options['action_id'] == action.id:
                self = self.with_context(from_pos_partner_editor=True)
        return super(ResPartner, self).get_views(views, options)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id, view_type, **options)
        if view_type == 'form' and self.env.context.get('from_pos_partner_editor'):
            # The POS UI opens the regular partner form, but its asset bundle
            # only ships a subset of the backend field widgets: every widget
            # the form inheritance chain brings along that is not part of the
            # bundle falls back to the default widget of its field type after
            # logging a "Missing widget" console warning. Strip those widget
            # attributes so the fallback happens silently. This runs after the
            # view cache on purpose: the stripping is context-dependent, and it
            # must also catch widgets other modules stamp dynamically in their
            # own _get_view overrides (e.g. partner_autocomplete).
            available = self._get_pos_available_field_widgets()
            arch = etree.fromstring(result['arch'])
            stripped = False
            for node in arch.xpath('//field[@widget]'):
                if node.get('widget') not in available:
                    node.attrib.pop('widget')
                    stripped = True
            if stripped:
                result['arch'] = etree.tostring(arch, encoding='unicode')
        return result

    @tools.ormcache()
    def _get_pos_available_field_widgets(self):
        """Return the names of the field widgets registered by the assets of
        the POS bundle, by scanning its resolved file list for static
        ``registry.category("fields").add(...)`` registrations."""
        widgets = set()
        for _path, full_path, *_ in self.env['ir.asset']._get_asset_paths(
            'point_of_sale._assets_pos', {}
        ):
            if not full_path or not str(full_path).endswith('.js'):
                continue
            try:
                with open(full_path, encoding='utf-8') as asset_file:
                    content = asset_file.read()
            except OSError:
                continue
            widgets.update(FIELD_WIDGET_REGISTRATION_RE.findall(content))
        return frozenset(widgets)

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])

        # Collect partner IDs from loaded orders
        loaded_order_partner_ids = {order['partner_id'] for order in data['pos.order']['data']}

        # Extract partner IDs from the tuples returned by get_limited_partners_loading
        limited_partner_ids = {partner[0] for partner in config_id.get_limited_partners_loading()}

        limited_partner_ids.add(self.env.user.partner_id.id)  # Ensure current user is included
        partner_ids = limited_partner_ids.union(loaded_order_partner_ids)
        return [('id', 'in', list(partner_ids))]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'id', 'name', 'street', 'city', 'state_id', 'country_id', 'vat', 'lang', 'phone', 'zip', 'mobile', 'email',
            'barcode', 'write_date', 'property_account_position_id', 'property_product_pricelist', 'parent_name', 'contact_address',
            'company_type',
        ]

    def _compute_pos_order(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)],
            ['parent_id'],
        )
        pos_order_data = self.env['pos.order']._read_group(
            domain=[('partner_id', 'in', all_partners.ids)],
            groupby=['partner_id'], aggregates=['__count']
        )
        self_ids = set(self._ids)

        self.pos_order_count = 0
        for partner, count in pos_order_data:
            while partner:
                if partner.id in self_ids:
                    partner.pos_order_count += count
                partner = partner.parent_id

    def action_view_pos_order(self):
        '''
        This function returns an action that displays the pos orders from partner.
        '''
        action = self.env['ir.actions.act_window']._for_xml_id('point_of_sale.action_pos_pos_form')
        if self.is_company:
            action['domain'] = [('partner_id.commercial_partner_id', '=', self.id)]
        else:
            action['domain'] = [('partner_id', '=', self.id)]
        return action

    def open_commercial_entity(self):
        return {
            **super().open_commercial_entity(),
            **({'target': 'new'} if self.env.context.get('target') == 'new' else {}),
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_if_pos_no_orders(self):
        if self.sudo().pos_order_ids:
            raise ValidationError(_('You cannot delete a customer that has point of sales orders. You can archive it instead.'))
