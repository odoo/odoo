import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";

export class CalendarSyncButtons extends Component {
    static props = {
        ...standardWidgetProps,
        record: { type: Object, optional: true },
        reloadModel: { type: Function, optional: true },
    };
    static template = "calendar.calendarSyncButtons";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({});
        onWillStart(async () => await this.initSyncValues())
    }

    async initSyncValues() {
        const [credentialStatus, syncStatus] = await Promise.all([
            rpc("/calendar/check_credentials"),
            this.orm.call("res.users", "check_synchronization_status", [[user.userId]]),
        ]);

        // this.googleCredentialsSet = true;
        // this.googleCredentialStatus = true;
        // this.googleSyncStatus = "sync_paused";

        this.googleCredentialsSet = credentialStatus['google_calendar'] ?? false;
        this.googleCredentialStatus = credentialStatus['google_calendar'];
        this.googleSyncStatus = syncStatus['google_calendar']

        this.microsoftCredentialsSet = credentialStatus['microsoft_calendar'] ?? false;
        this.microsoftCredentialStatus = credentialStatus['microsoft_calendar'];
        this.microsoftSyncStatus = syncStatus['microsoft_calendar']

        this.isSystemUser = await user.hasGroup("base.group_system");
    }
}

export const calendarSyncButtons = {
    component: CalendarSyncButtons,
};

registry.category("view_widgets").add("calendar_sync_buttons", calendarSyncButtons);
