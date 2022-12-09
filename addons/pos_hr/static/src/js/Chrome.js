/** @odoo-module */

import Chrome from "@point_of_sale/js/Chrome";
import Registries from "@point_of_sale/js/Registries";

const PosHrChrome = (Chrome) =>
    class extends Chrome {
        async start() {
            await super.start();
            if (this.env.pos.config.module_pos_hr) {
                this.showTempScreen("LoginScreen");
            }
        }
        get headerButtonIsShown() {
            return (
                !this.env.pos.config.module_pos_hr ||
                this.env.pos.get_cashier().role == "manager" ||
                this.env.pos.get_cashier_user_id() === this.env.pos.user.id
            );
        }
        showCashMoveButton() {
            return (
                super.showCashMoveButton() &&
                (!this.env.pos.cashier || this.env.pos.cashier.role == "manager")
            );
        }
        shouldShowCashControl() {
            if (this.env.pos.config.module_pos_hr) {
                return super.shouldShowCashControl() && this.env.pos.hasLoggedIn;
            }
            return super.shouldShowCashControl();
        }
    };

Registries.Component.extend(Chrome, PosHrChrome);

export default Chrome;
