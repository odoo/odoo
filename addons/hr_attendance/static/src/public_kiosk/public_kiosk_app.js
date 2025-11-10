import { App, whenReady, Component, proxy } from "@odoo/owl";
import { CardLayout } from "@hr_attendance/components/card_layout/card_layout";
import { KioskManualSelection } from "@hr_attendance/components/manual_selection/manual_selection";
import { makeEnv, startServices } from "@web/env";
import { getTemplate } from "@web/core/templates";
import { _t, appTranslateFn } from "@web/core/l10n/translation";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { KioskConfirmation } from "@hr_attendance/components/confirmation/confirmation";
import { KioskGreetings } from "@hr_attendance/components/greetings/greetings";
import { KioskPinCode } from "@hr_attendance/components/pin_code/pin_code";
import { KioskBarcodeScanner } from "@hr_attendance/components/kiosk_barcode/kiosk_barcode";
import { browser } from "@web/core/browser/browser";
import { isIosApp } from "@web/core/browser/feature_detection";
import { DocumentationLink } from "@web/views/widgets/documentation_link/documentation_link";
import { NewEmployeeDialog } from "@hr_attendance/components/new_employee_dialog/new_employee_dialog";
import { BreakDurationDialog } from "@hr_attendance/components/break_duration_dialog/break_duration_dialog";
import { session } from "@web/session";
import { services } from "@web/core/services";

const { DateTime } = luxon;

class kioskAttendanceApp extends Component {
    static template = "hr_attendance.public_kiosk_app";
    static props = {
        token: { type: String },
        companyId: { type: Number },
        companyName: { type: String },
        departments: { type: Array },
        kioskMode: { type: String },
        barcodeSource: { type: String },
        fromTrialMode: { type: Boolean },
        deviceTrackingEnabled: { type: Boolean },
        captureCheckInImage: { type: Boolean },
        breakManagementEnabled: { type: Boolean },
    };
    static components = {
        KioskBarcodeScanner,
        CardLayout,
        KioskManualSelection,
        KioskConfirmation,
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
        this.state = proxy({
            active_display: "settings",
            displayDemoMessage:
                browser.localStorage.getItem("hr_attendance.ShowDemoMessage") !== "false",
            streamAvailable: false,
            kioskMode: this.props.kioskMode,
            employeeData: null,
        });
        this.lockScanner = false;
        this.cameraCapture = null;
        this.lastManualSelection = null;
        this.lastBarcodeSelection = null;
        if (this.state.kioskMode === "settings" || this.props.fromTrialMode) {
            this.manualKioskMode = false;
            useBus(this.barcode.bus, "barcode_scanned", (ev) =>
                this.onBarcodeScanned(ev.detail.barcode)
            );
        } else if (this.state.kioskMode !== "manual") {
            useBus(this.barcode.bus, "barcode_scanned", (ev) =>
                this.onBarcodeScanned(ev.detail.barcode)
            );
            this.state.active_display = "main";
            this.manualKioskMode = false;
        } else {
            this.manualKioskMode = true;
            this.state.active_display = "manual";
        }
    }

    switchDisplay(screen) {
        const displays = ["main", "greet", "manual", "confirmation", "pin", "settings"];
        if (displays.includes(screen)) {
            this.state.active_display = screen;
        } else {
            this.state.active_display = "main";
        }
    }

    newSetUp() {
        this.dialogService.add(NewEmployeeDialog, { token: this.props.token });
    }

    async setSetting(mode) {
        await rpc("/hr_attendance/set_settings", {
            token: this.props.token,
            mode: mode,
        });
        this.state.kioskMode = mode;
        if (mode !== "manual") {
            this.manualKioskMode = false;
            this.state.active_display = "main";
        } else {
            this.manualKioskMode = true;
            this.state.active_display = "manual";
        }
    }

    async fetchEmployeeData(employeeId) {
        const employee = await rpc("attendance_employee_data", {
            token: this.props.token,
            employee_id: employeeId,
        });
        if (employee && employee.employee_name) {
            this.state.employeeData = employee;
            return employee;
        }
        return null;
    }

    async kioskEmployeeSelected(employeeId) {
        const employee = await this.fetchEmployeeData(employeeId);
        if (employee) {
            if (employee.use_pin) {
                this.switchDisplay("pin");
            } else if (this.props.captureCheckInImage && employee.attendance_state !== "checked_in") {
                this.switchDisplay("confirmation");
            } else {
                await this.onManualSelection(employeeId, false);
            }
        }
    }

    kioskReturn() {
        if (this.state.active_display === "settings") {
            history.back();
        } else if (["confirmation", "pin", "greet"].includes(this.state.active_display)) {
            this.switchDisplay(
                ["barcode_manual", "barcode"].includes(this.state.kioskMode) ? "main" : "manual"
            );
        } else if (
            (["manual", "barcode"].includes(this.state.kioskMode) ||
                (this.state.kioskMode === "barcode_manual" &&
                    this.state.active_display === "main")) &&
            this.props.fromTrialMode
        ) {
            this.switchDisplay("settings");
        } else if (this.state.kioskMode === "manual") {
            this.switchDisplay("manual");
        } else {
            this.switchDisplay("main");
        }
    }

    displayNotification(text) {
        this.notification.add(text, { type: "danger" });
    }

    displayServerNotification(notification) {
        if (!notification?.message) {
            return;
        }
        this.notification.add(notification.message, {
            type: notification.type,
        });
    }

    async makeRpcWithGeolocation(route, params) {
        if (!this.props.deviceTrackingEnabled || !navigator.geolocation || isIosApp()) {
            // iOS app lacks permissions or tracking disabled
            return rpc(route, { ...params });
        }

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
                        ...params,
                    });
                    resolve(result);
                },
                { enableHighAccuracy: true }
            );
        });
    }

    async onManualSelection(employeeId, enteredPin) {
        const pendingEmployee = this.state.employeeData;
        const isCheckingIn = pendingEmployee?.attendance_state !== "checked_in";
        const checkInImage =
            isCheckingIn && this.props.captureCheckInImage ? await this.cameraCapture?.() : null;
        const result = await this.makeRpcWithGeolocation("manual_selection", {
            token: this.props.token,
            employee_id: employeeId,
            pin_code: enteredPin,
            check_in_image: checkInImage,
        });
        if (result && result.attendance) {
            this.lastManualSelection = { employeeId, pinCode: enteredPin };
            this.lastBarcodeSelection = null;
            this.state.employeeData = result;
            this.displayServerNotification(result.notification);
            this.switchDisplay("greet");
        } else {
            if (enteredPin) {
                this.displayNotification(_t("Wrong Pin"));
            }
        }
    }

    async onBarcodeScanned(barcode) {
        if (this.lockScanner || this.state.active_display !== "main") {
            return;
        }
        this.lockScanner = true;
        this.ui.block();

        try {
            const preview = this.props.breakManagementEnabled
                ? await rpc("attendance_barcode_preview", {
                      barcode: barcode,
                      token: this.props.token,
                  })
                : null;
            if (this.props.breakManagementEnabled && !(preview && preview.employee_name)) {
                this.displayNotification(
                    _t("No employee corresponding to Badge ID '%(barcode)s.'", { barcode })
                );
                return;
            }
            const isCheckingIn = !preview || preview.attendance_state !== "checked_in";
            const checkInImage =
                isCheckingIn && this.props.captureCheckInImage ? await this.cameraCapture?.() : null;
            const result = await rpc("attendance_barcode_scanned", {
                barcode: barcode,
                token: this.props.token,
                check_in_image: checkInImage,
            });

            if (result && result.employee_name) {
                this.lastBarcodeSelection = { barcode, employeeId: result.id };
                this.lastManualSelection = null;
                this.state.employeeData = result;
                this.displayServerNotification(result.notification);
                this.switchDisplay("greet");
            } else {
                this.displayNotification(
                    _t("No employee corresponding to Badge ID '%(barcode)s.'", { barcode })
                );
            }
        } catch (error) {
            this.displayNotification(error?.data?.message || error?.message);
        } finally {
            this.lockScanner = false;
            this.ui.unblock();
        }
    }

    async continueAsBreakTime() {
        const employee = this.state.employeeData;
        if (!employee?.id) {
            this.kioskReturn(true);
            return;
        }

        const minutes = await this.requestBreakDuration(
            employee.employee_name,
            this._getAttendanceMaxBreakMinutes(employee)
        );
        if (minutes === null) {
            this.kioskReturn(true);
            return;
        }
        const breakDurationHours = (Number(minutes) || 0) / 60;

        this.ui.block();
        try {
            let result;
            if (this.lastBarcodeSelection?.employeeId === employee.id) {
                result = await rpc("update_last_break_duration", {
                    barcode: this.lastBarcodeSelection.barcode,
                    token: this.props.token,
                    break_duration: breakDurationHours,
                });
            } else {
                const pinCode = this.lastManualSelection?.employeeId === employee.id
                    ? this.lastManualSelection.pinCode
                    : false;
                result = await rpc("update_last_break_duration", {
                    token: this.props.token,
                    employee_id: employee.id,
                    pin_code: pinCode,
                    break_duration: breakDurationHours,
                });
            }

            if (result && result.attendance) {
                this.state.employeeData = result;
                this.displayServerNotification(result.notification);
                this.kioskReturn(true);
            } else {
                this.displayNotification(_t("Could not save break duration. Please identify again."));
                this.kioskReturn(true);
            }
        } catch (error) {
            this.displayNotification(error?.data?.message || error?.message);
            this.kioskReturn(true);
        } finally {
            this.ui.unblock();
        }
    }

    removeDemoMessage() {
        this.state.displayDemoMessage = false;
        browser.localStorage.setItem("hr_attendance.ShowDemoMessage", "false");
        return;
    }

    _getAttendanceMaxBreakMinutes(employeeData) {
        const attendance = employeeData?.attendance;
        if (!attendance?.check_in) {
            return null;
        }
        const checkInDate = deserializeDateTime(attendance.check_in);
        const checkOutDate = attendance.check_out ? deserializeDateTime(attendance.check_out) : DateTime.now();
        if (!(checkInDate?.isValid && checkOutDate?.isValid)) {
            return null;
        }
        const durationMinutes = checkOutDate.diff(checkInDate, "minutes").minutes;
        return Math.max(Math.floor(durationMinutes || 0), 0);
    }

    async requestBreakDuration(employeeName, maxMinutes = null) {
        return new Promise((resolve) => {
            let settled = false;
            const finalize = (value) => {
                if (!settled) {
                    settled = true;
                    resolve(value);
                }
            };
            this.dialogService.add(
                BreakDurationDialog,
                {
                    employeeName,
                    defaultMinutes: 0,
                    maxMinutes: typeof maxMinutes === "number" ? maxMinutes : undefined,
                    onConfirm: (minutes) => finalize(minutes),
                    onCancel: () => finalize(null),
                },
                {
                    onClose: () => finalize(null),
                }
            );
        });
    }

    setCameraCapture(capturePicture) {
        this.cameraCapture = capturePicture;
    }

    setStreamAvailable(isAvailable) {
        this.state.streamAvailable = isAvailable;
    }
}

export async function createPublicKioskAttendance(document, kiosk_backend_info) {
    await whenReady();
    const env = makeEnv();
    session.server_version_info = kiosk_backend_info.server_version_info;
    const app = new App({
        getTemplate,
        dev: env.debug,
        translateFn: appTranslateFn,
        translatableAttributes: ["data-tooltip"],
        plugins: services,
    });
    await startServices(env, app);
    const root = app.createRoot(kioskAttendanceApp, {
        env: env,
        props: {
            token: kiosk_backend_info.token,
            companyId: kiosk_backend_info.company_id,
            companyName: kiosk_backend_info.company_name,
            departments: kiosk_backend_info.departments,
            kioskMode: kiosk_backend_info.kiosk_mode,
            barcodeSource: kiosk_backend_info.barcode_source,
            fromTrialMode: kiosk_backend_info.from_trial_mode,
            deviceTrackingEnabled: kiosk_backend_info.device_tracking_enabled,
            captureCheckInImage: kiosk_backend_info.capture_check_in_image,
            breakManagementEnabled: kiosk_backend_info.break_management_enabled,
        },
    });
    return root.mount(document.body);
}
export default { kioskAttendanceApp, createPublicKioskAttendance };
