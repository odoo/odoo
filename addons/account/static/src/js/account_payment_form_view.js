odoo.define("account_payment.FormView", function (require) {
    "use strict";

    const FormRenderer = require('web.FormRenderer');
    const FormView = require("web.FormView");
    const viewRegistry = require("web.view_registry");

    const PaymentFormRenderer = FormRenderer.extend({
        /**
         * Share the chatter with the move that is behind the payment
         */
        _makeChatterContainerProps() {
            const props = this._super(...arguments);
            const move = this.state.data.move_id;
            if (move) {
                Object.assign(props, {
                    threadId: move.res_id,
                    threadModel: move.model,
                });
            }
            return props;
        },
    });

    const PaymentFormView = FormView.extend({
        config: Object.assign({}, FormView.prototype.config, {
            Renderer: PaymentFormRenderer,
        }),
    });

    viewRegistry.add("account_payment_form", PaymentFormView);
    return PaymentFormView;
});
