import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class AppointmentSyncButton extends Component {
    static props = {
        ...standardWidgetProps,
        calendarName: String,
        iconSrc: String,
    };
    static template = "appointment.AppointmentSyncButton";

    setup() {
        this.notification = useService("notification");
        this.pendingSync = false;
    }

    async onConnectCalendar() {
        if (!this.pendingSync) {
            const calendarData = this._getCalendarSyncData(this.props.calendarName);
            if (!calendarData) {
                return;
            }

            this.pendingSync = true;
            const syncResult = await rpc(
                calendarData.syncRoute,
                {
                    model: 'calendar.event',
                    fromurl: window.location.href,
                },
            );
            if (syncResult.status === "need_auth") {
                window.open(syncResult.url, "_blank");
            } else if (syncResult.status === calendarData.noNewEventKey || syncResult.status === "need_refresh") {
                this.notification.add(
                    _t("Your calendar is already configured and was successfully synchronized."),
                    { type: "success" },
                );
            } else {
                this.notification.add(
                    _t("The configuration has changed and synchronization is not possible anymore. Please reload the page."),
                    { type: "warning" },
                );
            }
            this.pendingSync = false;
        }
    }

    _getCalendarSyncData(calendarName) {
        // This should be overriden to add specific calendar data used for the synchronization.
        return false;
    }
}

export const appointmentSyncButton = {
    component: AppointmentSyncButton,
    extractProps: ({ attrs }) => ({
        calendarName: attrs.calendarName,
        iconSrc: attrs.iconSrc,
    }),
};

registry.category("view_widgets").add("appointment_sync_button", appointmentSyncButton);
