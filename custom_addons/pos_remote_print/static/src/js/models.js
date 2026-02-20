/** @odoo-module */

// Brittle PosOrder.prototype patch removed to resolve 'lines is undefined' crash.
// Custom fields (is_api_order, etc.) are now handled via backend-driven sync 
// in pos_order_api/models/pos_order.py -> _load_pos_data_fields.
