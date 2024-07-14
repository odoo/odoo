/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";

import { onWillStart } from "@odoo/owl";

export class AppointmentBookingListRenderer extends ListRenderer {
    static template = "appointment.AppointmentBookingListRenderer";

    setup() {
        super.setup();
        this.user = useService("user");

        onWillStart(async () => {
            this.isAppointmentManager = await this.user.hasGroup("appointment.group_appointment_manager");
        });
    }

    async onClickAddLeave() {
        this.env.services.action.doAction({
            name: _t("Add Closing Day(s)"),
            type: "ir.actions.act_window",
            res_model: "appointment.manage.leaves",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: {},
        });
    }
}
