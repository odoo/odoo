import { CashierName } from "@point_of_sale/app/components/navbar/cashier_name/cashier_name";
import { patch } from "@web/core/utils/patch";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";

patch(CashierName.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.pos.config.module_pos_hr) {
            useBarcodeReader({
                cashier: this.barcodeCashierAction.bind(this),
            });
        }
    },
    async barcodeCashierAction(code) {
        const employee = this.pos.accessRight.getEmployeeByBarcode(code.code);
        if (
            employee &&
            employee !== this.pos.accessRight.loggedCashier &&
            (!employee._pin || (await this.pos.accessRight.checkPin(employee)))
        ) {
            this.pos.setCashier(employee);
        }
        return employee;
    },
    //@Override
    get avatar() {
        if (this.pos.config.module_pos_hr) {
            const cashier = this.pos.accessRight.loggedCashier;
            if (!(cashier && cashier.id)) {
                return "";
            }
            return `/web/image/hr.employee.public/${cashier.id}/avatar_128`;
        }
        return super.avatar;
    },
    //@Override
    get cssClass() {
        if (this.pos.config.module_pos_hr) {
            return { oe_status: true };
        }
        return super.cssClass;
    },
    async onCashierClick() {
        if (!this.pos.config.module_pos_hr) {
            return;
        }
        return this.pos.selectCashier(false, true, true);
    },
});
