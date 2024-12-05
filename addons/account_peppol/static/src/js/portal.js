<<<<<<< master
import publicWidget from "@web/legacy/js/public/public_widget";
||||||| 371712bd1c245e56960d231df6b7592e95c37784
/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
=======
/** @odoo-module **/

import portalDetails from "@portal/js/portal";
>>>>>>> 92eab5e754befb2700c5a5c819017a34693b8ca8

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
        const method = document.querySelector("select[name='invoice_sending_method']").value;
        const divToToggle = document.querySelectorAll(".portal_peppol_toggle");
        for (const peppolDiv of divToToggle) {
            if (method === "peppol") {
                peppolDiv.classList.remove("d-none");
            } else {
                peppolDiv.classList.add("d-none");
            }
        }
    },

    _onSendingMethodChange() {
        this._showPeppolConfig();
    },
});
