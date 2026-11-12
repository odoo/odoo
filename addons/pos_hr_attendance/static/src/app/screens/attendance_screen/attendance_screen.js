import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";
import publicKiosk from "@hr_attendance/public_kiosk/public_kiosk_app";

export class PosAttendanceKiosk extends publicKiosk.kioskAttendanceApp {
    static template = "pos_hr_attendance.AttendanceKiosk";
}

export class AttendanceScreen extends Component {
    static template = "pos_hr_attendance.AttendanceScreen";
    static components = { PosAttendanceKiosk };
    static storeOnOrder = false;

    setup() {
        this.pos = usePos();
        useBarcodeReader({ cashier: () => {}, product: () => {} }, true);
        onWillStart(async () => {
            this.pos.attendanceKioskInfo ??= await this.pos.data.call(
                "pos.config",
                "get_attendance_kiosk_info",
                [this.pos.config.id]
            );
        });
    }
}

registry.category("pos_pages").add("AttendanceScreen", {
    name: "AttendanceScreen",
    component: AttendanceScreen,
    route: `/pos/ui/${odoo.pos_config_id}/attendance`,
    params: {},
});
