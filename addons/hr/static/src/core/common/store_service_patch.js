import { _t } from "@web/core/l10n/translation";
import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const storeServicePatch = {
    setup() {
        super.setup();
        /** @type {{[key: number]: {id: number, user_id: number, hasCheckedUser: boolean}}} */
        this.employees = {};
    },
    async getChat(person) {
        const { employeeId } = person;
        if (!employeeId) {
            return super.getChat(person);
        }
        let employee = this.employees[employeeId];
        if (!employee) {
            this.employees[employeeId] = { id: employeeId };
            employee = this.employees[employeeId];
        }
        if (!employee.user_id && !employee.hasCheckedUser) {
            employee.hasCheckedUser = true;
            const [employeeData] = await this.env.services.orm.silent.read(
                "hr.employee.public",
                [employee.id],
                ["user_id", "user_partner_id"],
                { context: { active_test: false } }
            );
            if (employeeData) {
                employee.user_id = employeeData.user_id[0];
                let user = this.users[employee.user_id];
                if (!user) {
                    this.users[employee.user_id] = { id: employee.user_id };
                    user = this.users[employee.user_id];
                }
                user.partner_id = employeeData.user_partner_id[0];
                this["res.partner"].insert({
                    display_name: employeeData.user_partner_id[1],
                    id: employeeData.user_partner_id[0],
                });
            }
        }
        if (!employee.user_id) {
            this.env.services.notification.add(
                _t("You can only chat with employees that have a dedicated user."),
                { type: "info" }
            );
            return;
        }
        return super.getChat({ userId: employee.user_id });
    },
};

patch(Store.prototype, storeServicePatch);
