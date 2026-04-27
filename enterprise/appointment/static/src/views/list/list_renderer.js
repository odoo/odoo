/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { AppointmentTypeActionHelper } from "@appointment/components/appointment_type_action_helper/appointment_type_action_helper";
import { ListRenderer } from "@web/views/list/list_renderer";
import { user } from "@web/core/user";

import { onWillStart } from "@odoo/owl";

export class AppointmentBookingListRenderer extends ListRenderer {
    static template = "appointment.AppointmentBookingListRenderer";

    setup() {
        super.setup();

        onWillStart(async () => {
            this.isAppointmentManager = await user.hasGroup("appointment.group_appointment_manager");
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

export class AppointmentTypeListRenderer extends ListRenderer {
    static template = "appointment.AppointmentTypeListRenderer";
    static components = {
        ...ListRenderer.components,
        AppointmentTypeActionHelper,
    };
}
