odoo.define('pos_deleted_audit_restaurant.pos_deleted_audit', function (require) {
    'use strict';

    var core = require('web.core');
    var models = require('point_of_sale.models');
    var gui = require('point_of_sale.gui');
    var popups = require('point_of_sale.popups');
    var rpc = require('web.rpc');

    var _t = core._t;
    var PopupWidget = popups.PopupWidget;

    models.load_fields('res.users', ['pos_delete_justification_enabled']);

    models.load_models([
        {
            model: 'pos.deleted.justification',
            fields: ['name', 'description', 'active'],
            domain: [['active', '=', true]],
            loaded: function (self, justifications) {
                self.pos_deleted_justifications = justifications || [];
            },
        },
    ]);

    var PosDeletedJustificationPopupWidget = PopupWidget.extend({
        template: 'PosDeletedJustificationPopupWidget',
        events: _.extend({}, PopupWidget.prototype.events, {
            'click .pos-justification-item': 'click_justification',
        }),
        show: function (options) {
            options = options || {};
            this._super(options);
            this.justifications = options.justifications || [];
            this.renderElement();
            this.$('textarea').focus();
        },
        click_confirm: function () {
            var value = this.$('textarea').val().trim();
            if (!value) {
                this.gui.show_popup('error', {
                    title: _t('Justificación requerida'),
                    body: _t('Debe ingresar una justificación para continuar.'),
                });
                return;
            }
            this.gui.close_popup();
            if (this.options.confirm) {
                this.options.confirm.call(this, value);
            }
        },
        click_justification: function (ev) {
            var text = $(ev.currentTarget).data('value') || '';
            var $textarea = this.$('textarea');
            var current = $textarea.val();
            if (current) {
                current += '\n';
            }
            $textarea.val((current || '') + text);
            $textarea.focus();
        },
    });

    gui.define_popup({name: 'pos_deleted_justification', widget: PosDeletedJustificationPopupWidget});

    var _super_orderline = models.Orderline.prototype;

    models.Orderline = models.Orderline.extend({
        set_quantity: function (quantity) {
            var current_qty = this.get_quantity();
            var is_decrease = false;
            var new_qty = quantity;

            if (quantity === 'remove') {
                is_decrease = true;
            } else {
                var quant = parseFloat(quantity) || 0;
                if (quant < current_qty) {
                    is_decrease = true;
                }
            }

            var cashier = this.pos.get_cashier() || this.pos.user;

            if (
                is_decrease &&
                cashier &&
                cashier.pos_delete_justification_enabled &&
                !this._deletion_prompt_active
            ) {
                var self = this;
                this._deletion_prompt_active = true;
                this.pos.gui.show_popup('pos_deleted_justification', {
                    title: _t('Justificación'),
                    justifications: this.pos.pos_deleted_justifications || [],
                    confirm: function (justification) {
                        self._deletion_prompt_active = false;
                        _super_orderline.set_quantity.call(self, new_qty);
                        self._create_deleted_audit(current_qty, new_qty, justification);
                    },
                    cancel: function () {
                        self._deletion_prompt_active = false;
                    },
                });
                return;
            }

            return _super_orderline.set_quantity.apply(this, arguments);
        },

        _create_deleted_audit: function (old_qty, new_qty, justification) {
            var removed_qty = 0;
            if (new_qty === 'remove') {
                removed_qty = old_qty;
            } else {
                var quant = parseFloat(new_qty) || 0;
                removed_qty = old_qty - quant;
            }

            if (removed_qty <= 0) {
                return;
            }

            var order = this.order;
            var cashier = this.pos.get_cashier() || this.pos.user;

            rpc.query({
                model: 'pos.deleted.product.audit',
                method: 'create_from_ui',
                args: [{
                    order_name: order.get_name(),
                    product_id: this.product.id,
                    removed_qty: removed_qty,
                    user_id: cashier ? cashier.id : false,
                    justification: justification,
                }],
            }).guardedCatch(function (error) {
                console.error('POS deletion audit failed', error);
            });
        },
    });
});
