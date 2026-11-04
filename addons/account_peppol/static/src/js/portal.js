/** @odoo-module **/

import portalDetails from "@portal/js/portal";

portalDetails.include({
    events: Object.assign({}, portalDetails.prototype.events, {
        'change select[name="invoice_sending_method"]': "_onSendingMethodChange",
    }),

    start() {
        this._showPeppolConfig();
        this.orm = this.bindService("orm");
        return this._super(...arguments);
    },

    _showPeppolConfig() {
        const method = document.querySelector("select[name='invoice_sending_method']")?.value;
        const isPeppol = method === "peppol";
        for (const peppolFieldset of document.querySelectorAll(".portal_peppol_toggle")) {
            peppolFieldset.classList.toggle("d-none", !isPeppol);
            peppolFieldset.disabled = !isPeppol;
        }
    },

    _onSendingMethodChange() {
        this._showPeppolConfig();
    },
});
