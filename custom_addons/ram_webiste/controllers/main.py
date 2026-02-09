import logging
_logger = logging.getLogger(__name__)
from odoo import http, _, tools
from odoo.http import request
import json
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class RamWebsiteController(http.Controller):
    @http.route(
        ["/ram/contact"],
        type="http",
        auth="public",
        website=True,
        methods=["GET", "POST"],
        csrf=True,
        sitemap=True,
    )
    def ram_contact(self, **post):
        if request.httprequest.method == "POST":
            name = (post.get("name") or "").strip()
            email = (post.get("email") or "").strip()
            phone = (post.get("phone") or "").strip()
            message = (post.get("message") or "").strip()

            # Minimal validation: keep UX smooth; admin can follow up from CRM.
            if name and (email or phone) and message:
                request.env["crm.lead"].sudo().create(
                    {
                        "name": _("Website Contact: %s") % name,
                        "contact_name": name,
                        "email_from": email,
                        "phone": phone,
                        "description": message,
                        "type": "lead",
                    }
                )
                return request.render("ram_webiste.ram_contact_thank_you", {})

            return request.render(
                "ram_webiste.ram_contact_page",
                {
                    "error": _(
                        "Please fill in your name, a way to reach you (email or phone), and your message."
                    ),
                    "values": {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "message": message,
                    },
                },
            )

        return request.render("ram_webiste.ram_contact_page", {"values": {}})

    @http.route(
        ["/ram/product/details"],
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def ram_product_details(self, product_id):
        product = request.env["product.template"].sudo().browse(int(product_id))
        if not product.exists() or not product.available_in_pos:
            return {"error": "Product not found or not available"}

        # 1. Handle Attributes
        attributes = []
        for line in product.attribute_line_ids:
            attributes.append({
                "id": line.id,
                "attribute_id": line.attribute_id.id,
                "name": line.attribute_id.name,
                "values": [
                    {
                        "id": v.id,
                        "name": v.name,
                        "price_extra": v.price_extra
                    } for v in line.product_template_value_ids
                ]
            })

        # 2. Handle Combos
        combos = []
        for combo in product.combo_ids:
            items = []
            for item in combo.combo_item_ids:
                items.append({
                    "id": item.id,
                    "product_id": item.product_id.id,
                    "name": item.product_id.name,
                    "price_extra": item.extra_price,
                    "image": f"/web/image/product.product/{item.product_id.id}/image_128",
                })
            combos.append({
                "id": combo.id,
                "name": combo.name,
                "qty_max": combo.qty_max,
                "qty_free": combo.qty_free,
                "items": items
            })

        # 3. Calculate tax-inclusive price
        # In Odoo 19, compute_all returns a dict with 'total_included'
        currency = request.website.currency_id
        res = product.taxes_id.compute_all(product.list_price, currency=currency, product=product)

        return {
            "id": product.id,
            "name": product.name,
            "list_price": res['total_included'],
            "tax_amount": res['total_included'] - res['total_excluded'],
            "image_url": f"/web/image/product.template/{product.id}/image_128",
            "attributes": attributes,
            "combos": combos,
        }

    @http.route(
        ["/ram/reviews"],
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
        readonly=True,
    )
    def ram_reviews_json(self, limit=12):
        reviews = (
            request.env["ram.website.review"]
            .sudo()
            .search([("is_published", "=", True)], order="sequence asc, id desc", limit=int(limit or 12))
        )
        return [
            {
                "id": r.id,
                "author_name": r.author_name,
                "rating": r.rating,
                "content": r.content,
                "source": r.source,
                "review_url": r.review_url,
                "author_photo_url": r.author_photo_url,
                "create_date": r.create_date.isoformat() if r.create_date else None,
            }
            for r in reviews
        ]

    @http.route(
        ["/ram/user/profile"],
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        website=True,
        readonly=True,
    )
    def ram_user_profile(self):
        user = request.env.user
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone or user.partner_id.phone,
            "street": user.partner_id.street,
            "city": user.partner_id.city,
            "zip": user.partner_id.zip,
        }

    # --- Cart Persistence API ---

    @http.route(
        ["/ram/cart/get"],
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def ram_cart_get(self):
        user = request.env.user
        cart = request.env["ram.website.cart"].sudo().get_cart_for_partner(user.partner_id.id)
        if not cart:
            return {"cart": []}
        
        lines = []
        for line in cart.line_ids:
            variation_data = json.loads(line.variation_data) if line.variation_data else {}
            lines.append({
                "product_id": line.product_id.id,
                "name": line.product_id.name,
                "qty": line.qty,
                "price": line.price_unit,
                "thumb": line.image_url,
                "variation_summary": line.variation_summary,
                "attribute_value_ids": variation_data.get("attribute_value_ids", []),
                "combo_line_ids": variation_data.get("combo_line_ids", []),
                "note": line.customer_note,
            })
        return {"cart": lines}

    @http.route(
        ["/ram/cart/sync"],
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def ram_cart_sync(self, cart_data):
        user = request.env.user
        Cart = request.env["ram.website.cart"].sudo()
        Line = request.env["ram.website.cart.line"].sudo()
        
        cart = Cart.get_cart_for_partner(user.partner_id.id)
        if not cart:
            cart = Cart.create({"partner_id": user.partner_id.id})
        
        # Clear existing lines and rebuild from sync data
        cart.line_ids.unlink()
        
        for item in cart_data:
            product_id = int(item.get("product_id"))
            variation_data = {
                "attribute_value_ids": item.get("attribute_value_ids", []),
                "combo_line_ids": item.get("combo_line_ids", []),
            }
            Line.create({
                "cart_id": cart.id,
                "product_id": product_id,
                "qty": float(item.get("qty", 1)),
                "price_unit": float(item.get("price", 0)),
                "variation_data": json.dumps(variation_data),
                "variation_summary": item.get("variation_summary", ""),
                "image_url": item.get("thumb"),
                "customer_note": item.get("note"),
            })
        return {"status": "success"}

    @http.route(["/ram/user/profile"], type="jsonrpc", auth="user", methods=["POST"], website=True)
    def ram_user_profile(self):
        partner = request.env.user.partner_id
        return {
            "name": partner.name,
            "phone": partner.phone,
            "email": partner.email,
            "street": partner.street,
            "city": partner.city,
            "zip": partner.zip,
            "state_id": partner.state_id.id,
            "country_id": partner.country_id.id,
        }

    @http.route(
        ["/ram/order/submit"],
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def ram_order_submit(self, **kwargs):
        order_data = kwargs.get('order_data')
        if not order_data:
            order_data = kwargs # Fallback if params passed directly
        """
        Submit a new order to the POS.
        Enhanced to handle combos, attributes, and partner creation.
        """
        # 1. Verify POS session
        session = request.env['pos.session'].sudo().search([
            ('state', '=', 'opened'),
            ('delivery_active', '=', True),
            ('config_id.accept_remote_orders', '=', True)
        ], limit=1)

        if not session:
            return {'error': _("Ordering is currently unavailable. No active session.")}

        # 2. Assign Partner (Enforce Portal User)
        if not request.session.uid:
            return {'error': _("Authentication Required: Please sign in to complete your order.")}
        
        user = request.env.user
        if user._is_public():
            return {'error': _("Authentication Required: Guest users cannot checkout. Please login or signup.")}

        partner = user.partner_id
        order_data['partner_id'] = partner.id
        
        # Update partner details if provided
        vals = {}
        if order_data.get('customer_phone') and not partner.phone:
            vals['phone'] = order_data.get('customer_phone')
        
        # Handle Address Updates (if changed by user)
        addr_fields = {
            'street': order_data.get('customer_street'),
            'city': order_data.get('customer_city'),
            'zip': order_data.get('customer_zip'),
        }
        for k, v in addr_fields.items():
            if v and partner[k] != v:
                vals[k] = v
        
        if vals:
            partner.sudo().write(vals)

        # 3. Handle Payment Method Mapping
        payment_mode = order_data.get('payment_method', 'counter')
        available_methods = session.config_id.payment_method_ids
        
        target_method = False
        if payment_mode == 'online':
            # Target a method that looks like a Card or Bank for simulation
            # BUT: We MUST avoid methods where 'is_online_payment' is True, as they trigger
            # the "accounting payment" validation in Odoo 19's pos_online_payment addon.
            target_method = available_methods.filtered(
                lambda m: ('card' in m.name.lower() or 'bank' in m.name.lower()) 
                and not getattr(m, 'is_online_payment', False)
                and not m.use_payment_terminal
            )[:1]
            
            # Sub-fallback: any non-terminal, non-online-flagged method
            if not target_method:
                target_method = available_methods.filtered(
                    lambda m: not getattr(m, 'is_online_payment', False) 
                    and not m.use_payment_terminal
                )[:1]
        
        if not target_method:
            # Prefer 'Cash' then first available for 'counter' or as fallback
            target_method = available_methods.filtered(lambda m: 'cash' in m.name.lower())[:1]
            
        if not target_method and available_methods:
            target_method = available_methods[0]
            
        if not target_method:
            return {'error': _("No payment methods configured for this POS.")}
            
        order_data['payment_method_id'] = target_method.id
        order_data['payment_method'] = payment_mode

        # 4. Augment order_data for POS API
        order_data['session_id'] = session.id
        order_data['source'] = 'native_web'
        
        import uuid
        if not order_data.get('uuid'):
            order_data['uuid'] = str(uuid.uuid4())

        try:
            order = request.env['pos.order'].sudo().create_api_order(order_data)
            
            # Capture created order details BEFORE attempting invoice
            # This ensures we have data to return even if invoicing fails (though we rollback anyway on error)
            # Actually, if invoicing fails, we might want to return the error, but we definitely can't access 'order' after rollback.
            
            order_id = order.id
            order_name = order.name
            order_ref = order.pos_reference
            
            # 6. Auto-Invoice for Online Payments
            if payment_mode == 'online' and order.state == 'paid':
                try:
                    order.sudo().action_pos_order_invoice()
                except Exception as inv_e:
                    # In Odoo, if this fails, the cursor might be invalidated or we might need to rollback.
                    # But 'order' was created in this transaction. If we rollback, 'order' is gone.
                    # We should probably catch this, log it, but NOT rollback the whole order if possible?
                    # However, standard Odoo behavior determines if we can recover.
                    # Safest approach for "Record does not exist": 
                    # If we rollback, we must NOT touch 'order'.
                    request.env.cr.rollback()
                    _logger.error(f"Failed to auto-invoice order {order_name}: {inv_e}")
                    return {'error': f"Order created but invoice failed. Please contact support. Ref: {order_name}"}

            return {
                'id': order.id,
                'name': order.name,
                'pos_reference': order.pos_reference,
                'status': order.delivery_status,
                'state': order.state,
                'amount_total': order.amount_total,
                'amount_tax': order.amount_tax,
                'invoice_id': order.account_move.id if order.account_move else False,
                'invoice_url': f"/my/invoices/{order.account_move.id}?access_token={order.account_move._portal_ensure_token()}" if order.account_move else False
            }
        except Exception as e:
            # If the creation itself failed, we land here.
            # If the auto-invoice failed and we rolled back, we might also land here if not caught above.
            request.env.cr.rollback()
            return {'error': str(e)}

# --- Portal Visibility Inheritance ---

class RamPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        # Use invoices instead of POS orders to avoid security issues for portal users
        if 'invoice_count' in counters:
            values['invoice_count'] = request.env['account.move'].search_count([
                ('move_type', '=', 'out_invoice'),
                ('partner_id', '=', request.env.user.partner_id.id)
            ])
        return values
