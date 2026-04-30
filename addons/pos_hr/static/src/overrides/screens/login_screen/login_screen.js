import { useCashierSelector } from "@pos_hr/app/select_cashier_mixin";
import { _t } from "@web/core/l10n/translation";
import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";
import { patch } from "@web/core/utils/patch";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { onWillUnmount, useExternalListener, useState } from "@odoo/owl";

patch(LoginScreen.prototype, {
    setup() {
        super.setup(...arguments);

        this.state = useState({
            pin: "",
        });

        if (this.pos.config.module_pos_hr) {
            this.barcodeReader = useService("barcode_reader");
            this.cashierSelector = useCashierSelector({
                onScan: (employee) => employee && this.selectOneCashier(employee),
                exclusive: true,
            });

            useAutofocus();
            useExternalListener(window, "keypress", async (ev) => {
                if (this.pos.login && ev.key === "Enter" && this.state.pin) {
                    const isBadge = this.pos.models["hr.employee"].some(
                        (emp) => emp._barcode === Sha1.hash(this.state.pin)
                    );
                    if (isBadge) {
                        this.barcodeReader.scan(this.state.pin);
                        this.state.pin = "";
                    } else {
                        await this.selectCashier(value, true);
                    }
                }
            });
        }

        onWillUnmount(() => {
            this.state.pin = "";
            this.pos.login = false;
        });
    },
    async selectCashier(pin = false, login = false, list = false) {
        return await this.cashierSelector(pin, login, list);
    },
    unlockRegister() {
        this.pos.login = true;
    },
    openRegister() {
        if (this.pos.config.module_pos_hr) {
            this.pos.login = true;
        } else {
            super.openRegister();
        }
    },
    async clickBack() {
        if (!this.pos.config.module_pos_hr) {
            super.clickBack();
            return;
        }

        if (this.pos.login) {
            this.state.pin = "";
            this.pos.login = false;
        } else {
            const employee = await this.selectCashier();
            if (employee && employee.user_id?.id === this.pos.user.id) {
                super.clickBack();
                return;
            } else if (employee) {
                this.pos.notification.add(
                    _t(
                        "Only the cashier linked to the logged-in user (%s) can proceed to the Backend.",
                        this.pos.user.name
                    ),
                    { type: "danger" }
                );
            }
        }
    },
    get backBtnName() {
        return this.pos.login && this.pos.config.module_pos_hr ? _t("Discard") : super.backBtnName;
    },
});
