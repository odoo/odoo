import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { qrCodeSrc } from "@point_of_sale/utils";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.company.account_fiscal_country_id?.code !== "JO") {
            return result;
        }

        result.headerData.l10n_jo_edi_pos_error = this.l10n_jo_edi_pos_error;
        result.l10n_jo_edi_pos_qr = this.l10n_jo_edi_pos_qr
            ? qrCodeSrc(this.l10n_jo_edi_pos_qr)
            : false;
        return result;
    },
});
