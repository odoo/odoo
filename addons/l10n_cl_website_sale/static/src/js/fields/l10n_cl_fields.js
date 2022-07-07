/** @odoo-module **/
import { WebsiteSale } from 'website_sale.website_sale';

WebsiteSale.include({
    events: Object.assign(WebsiteSale.prototype.events, {
        'click input[name="l10n_cl_type_document"]': '_onChangeClickTypeDocumentCl',
    }),
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        if ( document.getElementById('div_l10n_cl_additional_fields') ){
            this._onChangeClickTypeDocumentCl()
        }
        return def;
    },

    /**
     * Event click, hidden fields l10n_cl_activity_description if l10n_cl_sii_taxpayer_type is 'ticket'
     * @private
     */
    _onChangeClickTypeDocumentCl: function(ev) {
        var type_document = document.querySelector('input[name="l10n_cl_type_document"]')
        if ( type_document.checked ) {
            document.getElementById('div_l10n_cl_additional_fields').style.display = 'none'
        } else {
            document.getElementById('div_l10n_cl_additional_fields').style.display = 'flex'
        }
    },
});
