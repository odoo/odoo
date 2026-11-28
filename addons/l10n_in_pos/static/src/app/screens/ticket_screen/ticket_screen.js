import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    _getSearchFields() {
        const fields = super._getSearchFields(...arguments);
        if (this.pos.company.country_id?.code === "IN") {
            const invoiceNumber = fields.INVOICE_NUMBER;
            fields.INVOICE_NUMBER = {
                ...invoiceNumber,
                repr: (order) =>
                    [invoiceNumber.repr(order), order.l10n_in_b2c_invoice_number]
                        .filter(Boolean)
                        .join(" "),
                modelFields: [...invoiceNumber.modelFields, "l10n_in_b2c_invoice_number"],
            };
        }
        return fields;
    },
});
