
import { onWillUnmount, onMounted } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { HrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status"

patch(HrPresenceStatus.prototype, {
    setup() {
        super.setup();
        this.busService = this.env.services.bus_service;
        if (this.props.record.data.work_contact_id) {
            this.employeeAttendanceChannel = `hr_attendance_presence#${this.props.record.data.work_contact_id.id}`;
            this._presenceHandler = this._update_employee_presence.bind(this)
            onMounted(() => {
                this.busService.addChannel(this.employeeAttendanceChannel)
                this.busService.subscribe('presence_status', this._presenceHandler);
            })
            onWillUnmount(()=>{
                this.busService.unsubscribe('presence_status', this._presenceHandler);
                this.busService.deleteChannel(this.employeeAttendanceChannel);
            })
        }
    },
    _update_employee_presence(payload) {
        if (payload?.channel === this.employeeAttendanceChannel && payload?.data?.emp_id === this.props.record.resId) {
            this.props.record.data.hr_icon_display = payload.data.status;
        }
    }
})
