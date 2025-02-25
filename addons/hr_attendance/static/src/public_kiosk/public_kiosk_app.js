import { App, whenReady, Component, useState } from "@odoo/owl";
import { CardLayout } from "@hr_attendance/components/card_layout/card_layout";
import { KioskManualSelection } from "@hr_attendance/components/manual_selection/manual_selection";
import { makeEnv, startServices } from "@web/env";
import { getTemplate } from "@web/core/templates";
import { _t, appTranslateFn } from "@web/core/l10n/translation";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { KioskGreetings } from "@hr_attendance/components/greetings/greetings";
import { KioskPinCode } from "@hr_attendance/components/pin_code/pin_code";
import { KioskBarcodeScanner } from "@hr_attendance/components/kiosk_barcode/kiosk_barcode";
import { browser } from "@web/core/browser/browser";
import { isIosApp } from "@web/core/browser/feature_detection";
import { DocumentationLink } from "@web/views/widgets/documentation_link/documentation_link";
import { NewEmployeeDialog } from "@hr_attendance/components/new_employee_dialog/new_employee_dialog";
import { session } from "@web/session";

class kioskAttendanceApp extends Component{
    static template = "hr_attendance.public_kiosk_app";
    static props = {
        token: { type: String },
        companyId: { type: Number },
        companyName: { type: String },
        departments: { type: Array },
        kioskMode: { type: String },
        barcodeSource: { type: String },
        fromTrialMode: { type: Boolean },
        activeDisplay: { type: String },
    };
    static components = {
        KioskBarcodeScanner,
        CardLayout,
        KioskManualSelection,
        KioskGreetings,
        KioskPinCode,
        MainComponentsContainer,
        DocumentationLink,
    };

    setup() {
        this.dialogService = useService("dialog");
        this.barcode = useService("barcode");
        this.notification = useService("notification");
        this.ui = useService("ui");
        this.companyImageUrl = url("/web/binary/company_logo", {
            company: this.props.companyId,
        });
        this.state = useState({
            active_display: "settings",
            displayDemoMessage: browser.localStorage.getItem("hr_attendance.ShowDemoMessage") !== "false",
        });
        this.lockScanner = false;
        if (this.props.kioskMode === 'settings' || this.props.fromTrialMode){
            this.manualKioskMode = false;
            useBus(this.barcode.bus, "barcode_scanned", (ev) => this.onBarcodeScanned(ev.detail.barcode));
        }
        else if (this.props.kioskMode !== 'manual') {
            useBus(this.barcode.bus, "barcode_scanned", (ev) => this.onBarcodeScanned(ev.detail.barcode));
            this.state.active_display = "main";
            this.manualKioskMode = false;
        } else {
            this.manualKioskMode = true;
            this.state.active_display = "manual";
        }
    }

    switchDisplay(screen) {
        const displays = ["main", "greet", "manual", "pin", "settings"];
        if (displays.includes(screen)) {
            this.state.active_display = screen;
        } else {
            this.state.active_display = "main";
        }
    }

    newSetUp() {
        this.dialogService.add(NewEmployeeDialog, { 'token': this.props.token });
    }

    async setSetting(mode) {
        await rpc("/hr_attendance/set_settings", {
            token: this.props.token,
            mode: mode,
        });
        this.props.kioskMode = mode;
        if (mode !== "manual") {
            this.manualKioskMode = false;
            this.state.active_display = "main";
            this.props.kioskMode = mode;
        } else {
            this.manualKioskMode = true;
            this.state.active_display = "manual";
            this.props.kioskMode = "manual";
        }
    }

    async kioskConfirm(employeeId){
        const employee = await rpc('attendance_employee_data',
            {
                'token': this.props.token,
                'employee_id': employeeId
            })
        if (employee && employee.employee_name){
            if (employee.use_pin){
                this.employeeData = employee
                this.switchDisplay('pin')
            }else{
                await this.onManualSelection(employeeId, false)
            }
        }
    }

    kioskReturn() {
        if (this.state.active_display === "settings"){
            history.back();
        } else if (
            (["manual", "barcode"].includes(this.props.kioskMode) ||
                (this.props.kioskMode === "barcode_manual" &&
                    this.state.active_display === "main")) &&
            this.props.fromTrialMode
        ) {
            this.switchDisplay("settings");
        } else if (this.props.kioskMode === 'manual') {
            this.switchDisplay("manual");
        } else {
            this.switchDisplay("main");
        }
    }

    displayNotification(text){
        this.notification.add(text, { type: "danger" });
    }

    async makeRpcWithGeolocation(route, params) {
        if (!isIosApp()) { // iOS app lacks permissions to call `getCurrentPosition`
            return new Promise((resolve) => {
                navigator.geolocation.getCurrentPosition(
                    async ({ coords: { latitude, longitude } }) => {
                        const result = await rpc(route, {
                            ...params,
                            latitude,
                            longitude,
                        });
                        resolve(result);
                    },
                    async (err) => {
                        const result = await rpc(route, {
                            ...params
                        });
                        resolve(result);
                    },
                    { enableHighAccuracy: true }
                );
            });
        }
        else {
            return rpc(route, {...params})
        }
    }

    async onManualSelection(employeeId, enteredPin) {
        const result = await this.makeRpcWithGeolocation('manual_selection',
            {
                'token': this.props.token,
                'employee_id': employeeId,
                'pin_code': enteredPin
            })
        if (result && result.attendance) {
            this.employeeData = result
            this.switchDisplay('greet')
        }else{
            if (enteredPin){
                this.displayNotification(_t("Wrong Pin"))
            }
        }
    }

    async onBarcodeScanned(barcode){
        if (this.lockScanner || this.state.active_display !== 'main') {
            return;
        }
        this.lockScanner = true;
        this.ui.block();

        let result;
        try {
            result = await rpc("attendance_barcode_scanned", {
                barcode: barcode,
                token: this.props.token,
            });

            if (result && result.employee_name) {
                this.employeeData = result;
                this.switchDisplay("greet");
            } else {
                this.displayNotification(
                    _t("No employee corresponding to Badge ID '%(barcode)s.'", { barcode })
                );
            }
        } catch (error) {
            this.displayNotification(error.data.message);
        } finally {
            this.lockScanner = false;
            this.ui.unblock();
        }
    }

    removeDemoMessage() {
        this.state.displayDemoMessage = false;
        browser.localStorage.setItem("hr_attendance.ShowDemoMessage", "false");
        return;
    }
}

export async function createPublicKioskAttendance(document, kiosk_backend_info) {
    await whenReady();
    const env = makeEnv();
    await startServices(env);
    session.server_version_info = kiosk_backend_info.server_version_info;
    const app = new App(kioskAttendanceApp, {
        getTemplate,
        env: env,
        props:
            {
                token : kiosk_backend_info.token,
                companyId: kiosk_backend_info.company_id,
                companyName: kiosk_backend_info.company_name,
                departments: kiosk_backend_info.departments,
                kioskMode: kiosk_backend_info.kiosk_mode,
                barcodeSource: kiosk_backend_info.barcode_source,
                fromTrialMode: kiosk_backend_info.from_trial_mode,
            },
        dev: env.debug,
        translateFn: appTranslateFn,
        translatableAttributes: ["data-tooltip"],
    });
    return app.mount(document.body);
}
export default { kioskAttendanceApp, createPublicKioskAttendance };
