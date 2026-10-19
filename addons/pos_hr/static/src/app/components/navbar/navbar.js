import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.config.module_pos_hr) {
            useBarcodeReader({
                cashier: (code) =>
                    this.pos.setCashierFromBadge(
                        this.pos.accessRight.getEmployeeByBarcode(code.code)
                    ),
            });
        }
    },
});
