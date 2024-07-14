/** @odoo-module**/

import "@website/snippets/s_website_form/000"; // force deps
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.s_website_form.include({
    /**
     * @override
     */
    async send() {
        if (this.el.getAttribute("action").endsWith("/shop/l10n_mx_invoicing_info")) {
            return;
        }
        return this._super(...arguments);
    },
});
