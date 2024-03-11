/** @odoo-module **/

import { FormRenderer } from "@web/views/form/form_renderer";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";

const providerData = {
    'google': {
        'restart_sync_method': 'restart_google_synchronization',
        'sync_route': '/google_calendar/sync_data'
    },
    'microsoft': {
        'restart_sync_method': 'restart_microsoft_synchronization',
        'sync_route': '/microsoft_calendar/sync_data'
    }
}


export class CalendarProviderConfigFormRenderer extends FormRenderer {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.rpc = useService('rpc');
    }

    /**
     * Activate the external sync for the first time, after installing the
     * relevant submodule if necessary.
     *
     * @private
     */
    async onConnect(ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        if (!await this.props.record.save({stayInEdition: true})) {
            return;  // handled by view
        }
        await this.orm.call(
            this.props.record.resModel,
            'action_calendar_prepare_external_provider_sync',
            [this.props.record.resId]
        )
        // See google/microsoft_calendar for the origin of this shortened version
        const { restart_sync_method, sync_route } = providerData[this.props.record.data.external_calendar_provider];
        await this.orm.call(
            'res.users',
            restart_sync_method,
            [[session.uid]]
        );
        const response = await this.rpc(
            sync_route, {
                model: 'calendar.event',
                fromurl: window.location.href,
            }
        );
        await this._beforeLeaveContext();
        if (response.status === "need_auth") {
            window.location.assign(response.url);
        } else if (response.status === "need_refresh") {
            window.location.reload();
        }
    }
    /**
     * Hook to perform additional work before redirecting to external url or reloading.
     *
     * @private
     */
    async _beforeLeaveContext() {
        return Promise.resolve();
    }
}
