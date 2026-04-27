import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    _convertToDDMMYYYY(date) {
        const [day, month, year] = date.split("/");
        return `${day.padStart(2, "0")}${month.padStart(2, "0")}${year}`;
    },

    get isRefunded() {
        return this.lines.every((line) => line.qty < 0);
    },

    getRefundInfo(it_fiscal_printer_serial_number) {
        let { it_z_rep_number, it_fiscal_receipt_number, it_fiscal_receipt_date } = this;
        it_z_rep_number = it_z_rep_number.padStart(4, "0");
        it_fiscal_receipt_number = it_fiscal_receipt_number.padStart(4, "0");
        it_fiscal_receipt_date = this._convertToDDMMYYYY(it_fiscal_receipt_date);
        return `REFUND ${it_z_rep_number} ${it_fiscal_receipt_number} ${it_fiscal_receipt_date} ${it_fiscal_printer_serial_number}`;
    },
});
