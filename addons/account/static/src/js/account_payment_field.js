odoo.define('account.payment', function (require) {
    "use strict";

    const AbstractFieldOwl = require('web.AbstractFieldOwl');
    const fieldRegistry = require('web.field_registry_owl');
    const fieldUtils = require('web.field_utils');

    class ShowPaymentLineWidget extends AbstractFieldOwl {

        constructor(...args) {
            super(...args);
            this.popoverPosition = this.env._t.database.parameters.direction === "rtl" ? 'bottom' : 'left';
            this.info = JSON.parse(this.value);
            if (this.info) {
                this.info.content.forEach((k, v) => {
                    k.index = v;
                    // format amount into monetary widget
                    k.amount = fieldUtils.format.monetary(k.amount, {}, {
                        digits: k.digits, currency: { symbol: k.currency, position: k.position }
                    });
                    if (k.date) {
                        k.date = fieldUtils.format.date(fieldUtils.parse.date(k.date, {}, { isUTC: true }));
                    }
                });
            }
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        /**
         * @override
         * @returns {boolean}
         */
        get isSet() {
            return true;
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @override
         * @param {MouseEvent} event
         */
        _onOpenPayment(event) {
            const paymentId = parseInt(event.target.getAttribute('payment-id'));
            const moveId = parseInt(event.target.getAttribute('move-id'));
            let resModel;
            let id;
            if (paymentId !== undefined && !isNaN(paymentId)) {
                resModel = "account.payment";
                id = paymentId;
            } else if (moveId !== undefined && !isNaN(moveId)) {
                resModel = "account.move";
                id = moveId;
            }
            //Open form view of account.move with id = move_id
            if (resModel && id) {
                this.trigger('do_action', {'action': {
                    type: 'ir.actions.act_window',
                    res_model: resModel,
                    res_id: id,
                    views: [[false, 'form']],
                    target: 'current'
                }});
            }
        }
        /**
         * @private
         * @override
         * @param {MouseEvent} event
         */
        async _onOutstandingCreditAssign(event) {
            const id = parseInt(event.target.getAttribute('data-id')) || false;
            await this.env.services.rpc({
                model: 'account.move',
                method: 'js_assign_outstanding_line',
                args: [JSON.parse(this.value).move_id, id],
            });
            this.trigger('reload');
        }
        /**
         * @private
         * @override
         * @param {MouseEvent} event
         */
        async _onRemoveMoveReconcile(event) {
            const moveId = parseInt($(event.target).attr('move-id'));
            const partialId = parseInt($(event.target).attr('partial-id'));
            if (partialId !== undefined && !isNaN(partialId)) {
                await this.env.services.rpc({
                    model: 'account.move.line',
                    method: 'remove_move_reconcile',
                    args: [moveId, partialId],
                    context: { 'move_id': this.resId },
                });
                this.trigger('reload');
            }
        }
    }

    ShowPaymentLineWidget.template = "ShowPaymentInfo";

    fieldRegistry.add('payment', ShowPaymentLineWidget);

    return ShowPaymentLineWidget;

});
