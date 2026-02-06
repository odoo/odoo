import uuid
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

# Default Delivery Preset ID (configured in Odoo)
DELIVERY_PRESET_ID = 3

class PosOrder(models.Model):
    _inherit = 'pos.order'

    # ID to prevent duplicates (Idempotency)
    unique_uuid = fields.Char(string='Unique API UUID', help='Unique identifier for API orders', copy=False, index=True)
    
    # Source tracking
    is_api_order = fields.Boolean(string='Is API Order', default=False, readonly=True)
    api_source = fields.Selection([
        ('native_web', 'Native Website'),
        ('uber', 'Uber Eats'),
        ('doordash', 'DoorDash'),
        ('zomato', 'Zomato'),
        ('swiggy', 'Swiggy'),
        ('other', 'Other')
    ], string='API Source', readonly=True)
    
    # Delivery Status Workflow (Restaurant-side tracking)
    # Note: For Uber Eats, driver tracking is handled by Uber's app
    delivery_status = fields.Selection([
        ('received', 'Order Received'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('on_the_way', 'On the Way'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ], string='Delivery Status', default='received', tracking=True,
       help='Restaurant-side order status for delivery workflow')
    
    # Remote printing status
    is_remote_printed = fields.Boolean(string='Remote Printed', default=False, help="True if printed to kitchen via remote bus")
    remote_printer_lock = fields.Many2one('pos.session', string='Printer Lock', help="Session that claimed this print job")
    
    # Delivery Metadata
    api_customer_name = fields.Char(string='API Customer Name')
    api_customer_phone = fields.Char(string='API Customer Phone')
    api_delivery_address = fields.Text(string='API Delivery Address')
    api_order_notes = fields.Text(string='API Order Notes')

    _sql_constraints = [
        ('unique_uuid_uniq', 'unique(unique_uuid)', 'Order UUID must be unique!'),
    ]

    @api.model
    def create_api_order(self, order_data):
        """
        Create POS order directly using DB-first approach.
        Calculates totals manually to avoid compute errors.
        """
        # 1. Idempotency check
        unique_uuid = order_data.get('uuid')
        existing = self.search([('unique_uuid', '=', unique_uuid)], limit=1)
        if existing:
            _logger.info(f"Duplicate Order Ignored: {unique_uuid}")
            return existing

        # 2. Session resolution
        session_id = order_data.get('session_id')
        if not session_id:
            # Find open session, check delivery_active AND config setting
            session = self.env['pos.session'].search([
                ('state', '=', 'opened'),
                ('delivery_active', '=', True),
                ('config_id.accept_remote_orders', '=', True)
            ], limit=1)
            
            if not session:
                 raise UserError(_("No Open & Active Delivery Session found (or remote orders disabled in config). Online ordering is paused."))
        else:
            session = self.env['pos.session'].browse(session_id)
            if not session.delivery_active or not session.config_id.accept_remote_orders:
                 raise UserError(_("Delivery is currently paused for this session or POS configuration."))
        
        session_id = session.id
        
        # 3. Calculate Totals & Lines
        # We must calculate amount_tax, amount_total, price_subtotal explicitly
        
        total_paid = 0.0
        total_tax = 0.0
        lines_data = []
        
        fiscal_position = self.env['account.fiscal.position'].browse(order_data.get('fiscal_position_id'))
        
        for line in order_data['lines']:
            product = self.env['product.product'].browse(line['product_id'])
            qty = line['qty']
            price_unit = line.get('price_unit', product.lst_price)
            
            # Tax Calculation
            taxes = product.taxes_id.filtered(lambda t: t.company_id.id == session.config_id.company_id.id)
            if fiscal_position:
                taxes = fiscal_position.map_tax(taxes)
            
            price_subtotal = price_unit * qty
            price_subtotal_incl = price_subtotal
            
            # Compute taxes
            tax_res = taxes.compute_all(price_unit, session.currency_id, qty, product=product, partner=self.env['res.partner'].browse(order_data.get('partner_id')))
            
            price_subtotal = tax_res['total_excluded']
            price_subtotal_incl = tax_res['total_included']
            
            current_tax = price_subtotal_incl - price_subtotal
            total_tax += current_tax
            total_paid += price_subtotal_incl

            lines_data.append((0, 0, {
                'product_id': product.id,
                'qty': qty,
                'price_unit': price_unit,
                'price_subtotal': price_subtotal,
                'price_subtotal_incl': price_subtotal_incl,
                'tax_ids': [(6, 0, taxes.ids)],
                'full_product_name': product.name,
                'name': product.name,
            }))

        amount_total = total_paid # In POS, paid usually equals total
        
        # Override with provided total if minor rounding diffs (optional safety)
        if order_data.get('amount_paid'):
            # simple validation?
            pass

        # 4. Generate proper order sequences (critical for compliance/auditing)
        pos_reference, tracking_number = session.config_id._get_next_order_refs()
        sequence_number = int(
            session.config_id.order_seq_id
            ._next()
            .removeprefix(session.config_id.order_seq_id.prefix or '')
            .removesuffix(session.config_id.order_seq_id.suffix or '')
        )
        # Order name follows format: "Order XXXXX-XXX-XXXX"
        order_name = f"Order {session.config_id.id:05d}-{session.id:03d}-{sequence_number:04d}"

        # 5. Build Order Values
        order_vals = {
            'name': order_name,
            'pos_reference': pos_reference,
            'tracking_number': tracking_number,
            'sequence_number': sequence_number,
            'session_id': session_id,
            'preset_id': DELIVERY_PRESET_ID,  # Assign to Delivery preset (visible in Delivery tab)
            'delivery_status': 'received',     # Initial status for delivery workflow
            'lines': lines_data,
            'amount_tax': total_tax,
            'amount_total': amount_total,
            'amount_paid': amount_total,
            'amount_return': 0.0,
            'partner_id': order_data.get('partner_id'),
            'fiscal_position_id': fiscal_position.id if fiscal_position else False,
            'pricelist_id': session.config_id.pricelist_id.id,
            'company_id': session.config_id.company_id.id,
            'unique_uuid': unique_uuid,
            'is_api_order': True,
            'api_source': order_data.get('source', 'other'),
            'api_customer_name': order_data.get('customer_name'),
            'api_customer_phone': order_data.get('customer_phone'),
            'api_delivery_address': order_data.get('delivery_address'),
            'api_order_notes': order_data.get('notes'),
            'general_customer_note': order_data.get('notes'), # Odoo 19 standard field
            'state': 'paid', # Directly paid
            'payment_ids': [[0, 0, {
                'amount': amount_total,
                'payment_method_id': order_data['payment_method_id'],
                'name': uuid.uuid4().hex[:8],
            }]]
        }

        # 5. Create Order
        # We rely on Odoo's create to pick up the sequence.
        # If sequence locking is an issue, we recommend changing ir_sequence implementation to 'standard' for POS.
        
        try:
            order = self.create(order_vals)
            
            # 6. Trigger real-time sync in POS
            # Send to session-specific channel for immediate UI update
            self.env['bus.bus']._sendone(session._get_bus_channel_name(), 'NEW_REMOTE_ORDER', {
                'order_id': order.id,
                'uuid': order.unique_uuid,
                'source': order.api_source
            })

            return order

        except Exception as e:
            _logger.error(f"API Order Creation Failed: {e}")
            raise ValidationError(f"System Error: {str(e)}")

    # NOTE: Do NOT override _load_pos_data_fields for pos.order in Odoo 19.
    # The base PosOrder class doesn't define this method - it inherits an empty list from pos.load.mixin.
    # Order data is loaded via read_pos_data() which reads ALL fields directly.
    # Custom fields defined on the model are automatically included.

    @api.model
    def claim_remote_print(self, order_id, session_id):
        # ... (Existing claim logic) ...
        # Copied from previous step to keep file complete
        order = self.browse(order_id)
        if not order.exists():
            return False
        if order.is_remote_printed:
            return False
        if order.remote_printer_lock and order.remote_printer_lock.id != session_id:
            return False
        if not order.remote_printer_lock:
             order.write({
                 'remote_printer_lock': session_id,
                 'is_remote_printed': True
             })
             return True
        return False

    @api.model
    def update_delivery_status(self, order_id, new_status):
        """
        Update delivery status for an order and broadcast to POS.
        Valid statuses: received, preparing, ready, on_the_way, delivered, cancelled
        """
        valid_statuses = ['received', 'preparing', 'ready', 'on_the_way', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            raise ValidationError(f"Invalid status: {new_status}. Must be one of: {valid_statuses}")
        
        order = self.browse(order_id)
        if not order.exists():
            raise ValidationError(f"Order {order_id} not found")
        
        old_status = order.delivery_status
        order.delivery_status = new_status
        
        # Broadcast status change to POS session
        if order.session_id:
            self.env['bus.bus']._sendone(
                order.session_id._get_bus_channel_name(),
                'DELIVERY_STATUS_CHANGE',
                {
                    'order_id': order.id,
                    'old_status': old_status,
                    'new_status': new_status,
                    'pos_reference': order.pos_reference,
                }
            )
        
        _logger.info(f"Order {order.pos_reference} status changed: {old_status} -> {new_status}")
        return True