/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.PortalInvoicePagePayment = publicWidget.Widget.extend({
    selector: "#portal_pay",

    /**
     * Show the payment dialog when the context parameter is set.
     *
     * @returns {void}
     */
    start() {
        if (this.el.dataset.payment) {
            const paymentDialog = new Modal("#pay_with");
            paymentDialog.show();
        }
        return this._super(...arguments);
    },
});
