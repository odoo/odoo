odoo.define('sale.SaleOrderView', function (require) {
    "use strict";

    const FormController = require('web.FormController');
    const FormView = require('web.FormView');
    const viewRegistry = require('web.view_registry');
    const Dialog = require('web.Dialog');
    const core = require('web.core');
    const _t = core._t;

    const SaleOrderFormController = FormController.extend({
        custom_events: _.extend({}, FormController.prototype.custom_events, {
            open_discount_wizard: '_onOpenDiscountWizard',
        }),

        // -------------------------------------------------------------------------
        // Handlers
        // -------------------------------------------------------------------------

        /**
         * Handler called if user changes the discount field in the sale order line.
         * The wizard will open only if
         *  (1) Sale order line is 3 or more
         *  (2) First sale order line is changed to discount
         *  (3) Discount is the same in all sale order line
         */
        _onOpenDiscountWizard(ev) {
            const orderLines = this.renderer.state.data.order_line.data;
            const recordData = ev.target.recordData;
            const isEqualDiscount = orderLines.slice(1).every(line => line.data.discount === recordData.discount);
            if (orderLines.length >= 3 && recordData.sequence === orderLines[0].data.sequence && isEqualDiscount) {
                Dialog.confirm(this, _t("Do you want to apply this discount to all order lines?"), {
                    confirm_callback: () => {
                        orderLines.slice(1).forEach((line) => {
                            this.trigger_up('field_changed', {
                                dataPointID: this.renderer.state.id,
                                changes: {order_line: {operation: "UPDATE", id: line.id, data: {discount: orderLines[0].data.discount}}},
                            });
                        });
                    },
                });
            }
        },
    });

    const SaleOrderView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: SaleOrderFormController,
        }),
    });

    viewRegistry.add('sale_discount_form', SaleOrderView);

    return SaleOrderView;

});
