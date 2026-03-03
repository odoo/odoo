import { _t } from "@web/core/l10n/translation";
import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

/** @type {import("models").Store} */
const storeServicePatch = {
    async getChat(person) {
        const { employeeId } = person;
        if (!employeeId) {
            return super.getChat(person);
        }
        const employeePublic = await this["hr.employee.public"].getOrFetch(employeeId, [
            "employee_id",
        ]);
        if (!employeePublic?.employee_id?.user_id) {
            this.env.services.notification.add(
                _t("You can only chat with employees that have a dedicated user."),
                { type: "info" }
            );
            return;
        }
        return super.getChat({ userId: employeePublic.employee_id.user_id });
    },
    /** @param {import("models").HrEmployee[]} employees */
    getRelevantEmployee(employees) {
        const activeEmployees = (employees ?? []).filter((e) => e.active);
        const activeCompanyId = user.activeCompany?.id;
        const sortedEmployees = activeEmployees.sort(
            (e1, e2) =>
                (e2.company_id?.id === activeCompanyId) - (e1.company_id?.id === activeCompanyId) ||
                (e1.user_id?.id ?? Infinity) - (e2.user_id?.id ?? Infinity) ||
                e2.id - e1.id
        );
        return sortedEmployees[0];
    },
};

patch(Store.prototype, storeServicePatch);
