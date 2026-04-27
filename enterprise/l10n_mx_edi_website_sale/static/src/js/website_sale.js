/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({

    events: Object.assign({}, WebsiteSale.prototype.events, {
        'click input[name="need_invoice"]': '_onChangeNeedInvoice',
    }),

    _onChangeNeedInvoice: function (ev) {
        if ($("input:radio[value='1']")[0].checked) {
            $('.div_l10n_mx_edi_additional_fields').show();
        } else {
            $('.div_l10n_mx_edi_additional_fields').hide();
        }
    },
});
