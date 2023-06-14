/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ThreadService, getChat } from "@mail/core/common/thread_service";
import { patch } from "web.utils";
import { patchFn } from "@mail/utils/common/patch";
import { insertPersona } from "@mail/core/common/persona_service";

let notificationService;
let orm;
/** @type {import("@mail/core/common/store_service").Store} */
let store;

patchFn(getChat, async function (person) {
    const { employeeId } = person;
    const _super = this._super.bind(this);
    if (!employeeId) {
        return _super(person);
    }
    let employee = store.employees[employeeId];
    if (!employee) {
        store.employees[employeeId] = { id: employeeId };
        employee = store.employees[employeeId];
    }
    if (!employee.user_id && !employee.hasCheckedUser) {
        employee.hasCheckedUser = true;
        const [employeeData] = await orm.silent.read(
            "hr.employee.public",
            [employee.id],
            ["user_id", "user_partner_id"],
            {
                context: { active_test: false },
            }
        );
        if (employeeData) {
            employee.user_id = employeeData.user_id[0];
            let user = store.users[employee.user_id];
            if (!user) {
                store.users[employee.user_id] = { id: employee.user_id };
                user = store.users[employee.user_id];
            }
            user.partner_id = employeeData.user_partner_id[0];
            insertPersona({
                displayName: employeeData.user_partner_id[1],
                id: employeeData.user_partner_id[0],
                type: "partner",
            });
        }
    }
    if (!employee.user_id) {
        notificationService.add(
            _t("You can only chat with employees that have a dedicated user."),
            { type: "info" }
        );
        return;
    }
    return _super({ userId: employee.user_id });
});

patch(ThreadService.prototype, "hr", {
    setup(env, services) {
        this._super(...arguments);
        notificationService = services.notification;
        orm = services.orm;
        store = services["mail.store"];
    },
});
