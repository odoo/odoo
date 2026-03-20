/** @odoo-module */

import { onWillUnmount, onMounted } from "@odoo/owl";
import { hrPresenceStatus, HrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(HrPresenceStatus.prototype, {
    setup() {
        super.setup();

        this.busService = this.env.services.bus_service;
        this._onPresenceStatus = this._onPresenceStatus.bind(this);

        this.employeeAttendanceChannel = `hr.employee_${this.props.record.resId}`;
        this.notificationType = "hr.employee/presence";

        onMounted(() => this._mounted());
        onWillUnmount(() => this._willUnmount());
    },

    _mounted() {
        this.busService.addChannel(this.employeeAttendanceChannel);
        this.busService.subscribe(this.notificationType, this._onPresenceStatus);
    },

    _willUnmount() {
        this.busService.unsubscribe(this.notificationType, this._onPresenceStatus);
        this.busService.deleteChannel(this.employeeAttendanceChannel);
    },

    /** Handle incoming hr.employee/presence notifications. */
    _onPresenceStatus(payload) {
        if (payload?.employee_id === this.props.record.resId) {
            this.props.record.data = {
                ...this.props.record.data,
                hr_presence_state: payload.hr_presence_state,
                hr_icon_display: payload.hr_icon_display,
            };
        }
    },

    get label() {
        if (this.value === 'presence_present') {
            const hasUser = this.props.record.data.user_id;
            if (!hasUser) {
                return _t("Present (untracked)");
            }
        } else if (this.value === 'presence_out_of_working_hour') {
            return _t("Off-Hours");
        }
        return super.label;
    },
});

Object.assign(hrPresenceStatus, {
    fieldDependencies: [
        ...hrPresenceStatus.fieldDependencies,
        { name: "user_id", type: "many2one" },
    ],
});
