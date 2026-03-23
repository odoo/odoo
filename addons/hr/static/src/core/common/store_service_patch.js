import { _t } from "@web/core/l10n/translation";
import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";

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
};

patch(Store.prototype, storeServicePatch);
