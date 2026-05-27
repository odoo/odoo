// Part of Odoo. See LICENSE file for full copyright and licensing details.

import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    get showCloseRegisterButton() {
        if (!this.pos.isPhilippinesCompany()) {
            return super.showCloseRegisterButton;
        }
        const config = this.pos.config;
        if (!config.module_pos_hr || this.pos.employeeIsAdmin) {
            return true;
        }
        if (this.pos.getCashierUserId() === this.pos.session.user_id?.id) {
            return true;
        }
        if (!config.l10n_ph_basic_can_close_register) {
            return false;
        }
        const cashierId = this.pos.getCashier()?.id;
        return (config.basic_employee_ids || []).some((e) => e.id === cashierId);
    },
});
