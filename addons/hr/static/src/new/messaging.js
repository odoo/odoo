/** @odoo-module */

import { Messaging } from "@mail/new/messaging";

import { patch } from "web.utils";

patch(Messaging.prototype, "hr", {
    setup(...args) {
        this._super(...args);
        this.state.employees = {};
    },
    async getChat(person) {
        const { employeeId } = person;
        const _super = this._super.bind(this);
        if (!employeeId) {
            return _super(person);
        }
        let employee = this.state.employees[employeeId];
        if (!employee) {
            this.state.employees[employeeId] = { id: employeeId };
            employee = this.state.employees[employeeId];
        }
        if (!employee.user_id && !employee.hasCheckedUser) {
            employee.hasCheckedUser = true;
            const [employeeData] = await this.orm.silent.read(
                "hr.employee.public",
                [employee.id],
                ["user_id", "user_partner_id"],
                {
                    context: { active_test: false },
                }
            );
            if (employeeData) {
                employee.user_id = employeeData.user_id[0];
                let user = this.state.users[employee.user_id];
                if (!user) {
                    this.state.users[employee.user_id] = { id: employee.user_id };
                    user = this.state.users[employee.user_id];
                }
                user.partner_id = employeeData.user_partner_id[0];
            }
        }
        if (!employee.user_id) {
            this.notification.add(
                this.env._t("You can only chat with employees that have a dedicated user."),
                { type: "info" }
            );
            return;
        }
        return _super({ userId: employee.user_id });
    },
});
