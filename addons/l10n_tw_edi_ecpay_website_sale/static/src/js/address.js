/** @odoo-module **/
import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { CustomerAddress } from '@portal/interactions/address';


patch(CustomerAddress.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            'input[name="company_name"]': {
                't-on-input': this._onChangeCompanyName.bind(this),
            },
        });
    },
    _onChangeCompanyName(ev) {
        const companyName = this.addressForm.o_company_name.value;
        if (document.getElementById("l10n_tw_edi_require_paper_format")) {
            if (companyName) {
                this._hideInput("l10n_tw_edi_require_paper_format");
            } else {
                this._showInput("l10n_tw_edi_require_paper_format");
            }
        }
    },
});
