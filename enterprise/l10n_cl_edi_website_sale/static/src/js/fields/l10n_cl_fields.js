/** @odoo-module **/
import { WebsiteSale } from "@website_sale/js/website_sale";

WebsiteSale.include({
    events: Object.assign(WebsiteSale.prototype.events, {
        'click input[name="l10n_cl_type_document"]': "_onClTypeDocumentClick",
    }),
    /**
     * @override
     */
    start() {
        const def = this._super(...arguments);
        if (document.getElementById("div_l10n_cl_additional_fields")) {
            this._onClTypeDocumentClick();
        }
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Event click, hidden fields l10n_cl_activity_description
     * if l10n_cl_sii_taxpayer_type is 'ticket'
     *
     * @private
     */
    _onClTypeDocumentClick() {
        const typeDocumentEl = document.querySelector('input[name="l10n_cl_type_document"]');
        const checked = typeDocumentEl.checked ? "none" : "flex";
        document.getElementById("div_l10n_cl_additional_fields").style.display = checked;
    },
});
