import { CashierName } from "@point_of_sale/app/navbar/cashier_name/cashier_name";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(CashierName.prototype, {
    setup() {
        super.setup(...arguments);
        this.printer = useService("printer");
    },
    async selectCashier(pin = false, login = false, list = false) {
        const current_cashier_id = this.pos.get_cashier().id;
        let toClock = true;
        if (this.pos.useBlackBoxBe()) {
            if (this.pos.checkIfUserClocked(current_cashier_id)) {
                await this.pos.clock(this.printer, false);
                toClock = false;
            }
        }
        await super.selectCashier(...arguments);
        const new_cashier_id = this.pos.get_cashier().id;
        if (this.pos.useBlackBoxBe()) {
            if (new_cashier_id !== current_cashier_id) {
                if (!this.pos.checkIfUserClocked(new_cashier_id)) {
                    await this.pos.clock(this.printer, true);
                }
            } else {
                if (toClock) {
                    await this.pos.clock(this.printer, true);
                }
            }
            this.pos.user_session_status = await this.pos.getUserSessionStatus();
        }
        return;
    },
    get userStatus() {
        return this.pos.user_session_status ? _t("In") : _t("Out");
    },
});
