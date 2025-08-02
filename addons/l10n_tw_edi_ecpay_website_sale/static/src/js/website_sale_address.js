/** @odoo-module **/
import websiteSaleAddress from "@website_sale/js/address";

websiteSaleAddress.include({
    events: Object.assign({}, websiteSaleAddress.prototype.events, {
        "input input[name='company_name']": "_onChangeCompanyName",
    }),

    _onChangeCompanyName(ev) {
        const comapnyName = this.addressForm.o_company_name.value;

        if (comapnyName) {
            this._hideInput("l10n_tw_edi_require_paper_format");
        } else {
            this._showInput("l10n_tw_edi_require_paper_format");
        }
    },
});
