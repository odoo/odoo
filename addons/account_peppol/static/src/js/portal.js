/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.portalDetails = publicWidget.Widget.extend({
    selector: '.o_portal_details',
    events: {
        'change select[name="invoice_sending_method"]': '_onSendingMethodChange',
    },

    start() {
        this._showPeppolConfig();
        this.orm = this.bindService("orm");
        return this._super.apply(this, arguments);
    },

    _showPeppolConfig() {
        const method = document.querySelector("select[name='invoice_sending_method']").value;
        const divToToggle = document.querySelectorAll(".portal_peppol_toggle");
        for (const peppolDiv of divToToggle) {
            if (method === "peppol") {
                peppolDiv.classList.remove("d-none")
            } else {
                peppolDiv.classList.add("d-none")
            }
        }
    },

    _onSendingMethodChange() {
        this._showPeppolConfig();
    },
});
