/** @odoo-module **/

import { FormRenderer } from "@web/views/form/form_renderer";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";

const EXTERNAL_CALENDAR_PARAMETERS = {
    google: {
        caption: 'Google',
        restart_sync_method: 'restart_google_synchronization',
        sync_route: '/google_calendar/sync_data',
    },
    microsoft: {
        caption: 'Outlook',
        restart_sync_method: 'restart_microsoft_synchronization',
        sync_route: '/microsoft_calendar/sync_data',
    }
};


export class ConfigureExternalSyncWizardFormRenderer extends FormRenderer {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.rpc = useService('rpc');
    }

    async onConnect(ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        const data = this.props.record.data;
        await this.orm.call(
            this.props.record.resModel,
            'action_configure_with_optional_install',
            [data]
        )
        return this._activateFirstSync(data.external_calendar_provider);
    }
    /**
     * Activates the external sync for the first time, when the relevant submodule
     * was just installed and the app not yet refreshed.
     *
     * @param {'google'|'microsoft'} externalCalendarProvider
     * @private
     */
    async _activateFirstSync(externalCalendarProvider) {
        const externalCalendarParameters = EXTERNAL_CALENDAR_PARAMETERS[externalCalendarProvider];
        // See google/microsoft_calendar for the origin of this shortened version
        try {
            await this.orm.call(
                'res.users',
                externalCalendarParameters.restart_sync_method,
                [[session.uid]]
            );
            const response = await this.rpc(
                externalCalendarParameters.sync_route, {
                    model: 'calendar.event',
                    fromurl: window.location.href,
                }
            );
            if (response.status !== "need_auth") {
                throw `Unhandled route response status '${response.status}'.`;
            }
            await this._beforeRedirect();
            window.location.assign(response.url);
        } catch (_) { // Let the freshly installed module take over
            window.location.reload();
        }
    }
    /**
     * Hook to perform additional work before redirecting to external url
     *
     * @private
     */
    async _beforeRedirect() {
        return Promise.resolve();
    }
}
