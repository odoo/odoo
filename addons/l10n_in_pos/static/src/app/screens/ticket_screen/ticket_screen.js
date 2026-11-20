import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    _getSearchFields() {
        const fields = super._getSearchFields(...arguments);
        if (this.pos.company.country_id?.code === "IN") {
            fields.L10N_IN_B2C_INVOICE_NUMBER = {
                repr: (order) => order.l10n_in_b2c_invoice_number || "",
                displayName: _t("B2C Invoice Number"),
                modelFields: ["l10n_in_b2c_invoice_number"],
            };
        }
        return fields;
    },
});
