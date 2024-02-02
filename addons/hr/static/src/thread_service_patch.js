/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { ThreadService } from "@mail/core/common/thread_service";
import { patch } from "@web/core/utils/patch";

/** @type {import("@mail/core/common/thread_service").ThreadService} */
const threadServicePatch = {
    async checkCanChat(persona) {
        if (persona.employeeId) {
            if (!persona.userId) {
                const [employeeData] = await this.orm.silent.read(
                    "hr.employee.public",
                    [persona.employeeId],
                    ["user_id", "user_partner_id"],
                    {
                        context: { active_test: false },
                    }
                );
                if (employeeData) {
                    persona.userId = employeeData.user_id[0];
                    persona.partnerId = employeeData.user_partner_id[0];
                    persona.displayName = employeeData.user_partner_id[1];
                }
            }
            if (!persona.userId) {
                this.notificationService.add(
                    _t("You can only chat with employees that have a dedicated user."),
                    { type: "info" }
                );
                return;
            }
        }
        return super.checkCanChat(persona);
    },
};

patch(ThreadService.prototype, threadServicePatch);
