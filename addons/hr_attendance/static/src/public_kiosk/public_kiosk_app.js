import { App, whenReady, Component, useState, onWillStart } from "@odoo/owl";
import { CardLayout } from "@hr_attendance/components/card_layout/card_layout";
import { KioskManualSelection } from "@hr_attendance/components/manual_selection/manual_selection";
import { makeEnv, startServices } from "@web/env";
import { getTemplate } from "@web/core/templates";
import { _t } from "@web/core/l10n/translation";
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
import { session } from "@web/session";

function isAlphaNumeric(str) {
    return /^[a-zA-Z0-9]+$/.test(str);
}

/**
* Maps the raw keys from a barcode scanner to the English (US) keyboard layout.
* @param {Array<{code: string, shiftKey: boolean}>} rawKeysBarcode - Array of key event objects from the barcode scanner.
* @returns {string} The decoded alphanumeric string as if typed on an English keyboard.
*/
function mapCodeToEnglishKeyboard(rawKeysBarcode) {
    const EN_US_KEYBOARD_MAP = {
        // Number row
        'Digit0': '0', 'Digit1': '1', 'Digit2': '2', 'Digit3': '3', 'Digit4': '4',
        'Digit5': '5', 'Digit6': '6', 'Digit7': '7', 'Digit8': '8', 'Digit9': '9',
        // Letters (QWERTY)
        'KeyA': 'a', 'KeyB': 'b', 'KeyC': 'c', 'KeyD': 'd', 'KeyE': 'e',
        'KeyF': 'f', 'KeyG': 'g', 'KeyH': 'h', 'KeyI': 'i', 'KeyJ': 'j',
        'KeyK': 'k', 'KeyL': 'l', 'KeyM': 'm', 'KeyN': 'n', 'KeyO': 'o',
        'KeyP': 'p', 'KeyQ': 'q', 'KeyR': 'r', 'KeyS': 's', 'KeyT': 't',
        'KeyU': 'u', 'KeyV': 'v', 'KeyW': 'w', 'KeyX': 'x', 'KeyY': 'y', 'KeyZ': 'z',
        // Numpad numbers (optional, useful for barcode scanners sometimes)
        'Numpad0': '0', 'Numpad1': '1', 'Numpad2': '2', 'Numpad3': '3', 'Numpad4': '4',
        'Numpad5': '5', 'Numpad6': '6', 'Numpad7': '7', 'Numpad8': '8', 'Numpad9': '9',
    };

    return rawKeysBarcode.map(keyEvent => {
        const key = EN_US_KEYBOARD_MAP[keyEvent.code];
        if (key)
            return keyEvent.shiftKey ? key.toUpperCase() : key;
        return '';
    }).join('');
}

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
        this.barcode = useService("barcode");
        this.notification = useService("notification");
        this.ui = useService("ui");
        this.companyImageUrl = url("/web/binary/company_logo", {
            company: this.props.companyId,
        });
        this.state = useState({
            barcode: false,
            barcodeIsSet: false,
            active_display: "settings",
            displayDemoMessage: browser.localStorage.getItem("hr_attendance.ShowDemoMessage") !== "false",
        });
        this.lockScanner = false;
        if (this.props.kioskMode === 'settings' || this.props.fromTrialMode){
            this.manualKioskMode = false;
            useBus(this.barcode.bus, "barcode_scanned", this.extractAndScanBarcode);
        }
        else if (this.props.kioskMode !== 'manual') {
            useBus(this.barcode.bus, "barcode_scanned", this.extractAndScanBarcode);
            this.state.active_display = "main";
            this.manualKioskMode = false;
        } else {
            this.manualKioskMode = true;
            this.state.active_display = "manual";
        }
        onWillStart( async () => {
            this.isFreshDb = await rpc("/hr_attendance/is_fresh_db", { token: this.props.token });
        });
    }

    async setBadgeID() {
        let barcode = this.state.barcode;
        if (barcode) {
            const result = await rpc("/hr_attendance/set_user_barcode", { token: this.props.token, barcode, });
            if (result) {
                this.notification.add(_t("Your badge Id is now set, you can scan your badge."), { type: 'success', });
            } else {
                this.notification.add(_t("Your badge has already been set."), { type: 'danger', });
            }
            this.state.barcodeIsSet = true;
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

    extractAndScanBarcode(ev) {
        let barcode = ev.detail.barcode;
        // When the client has a different keyboard layout than the one used to generate the RFIDs,
        // the barcode reader generates a different (unreadable) sequence of keys.
        // As a fallback, we map the raw keys to the English keyboard layout.
        if(!isAlphaNumeric(barcode) && ev.detail.rawKeysBarcode)
            barcode = mapCodeToEnglishKeyboard(ev.detail.rawKeysBarcode);
        this.onBarcodeScanned(barcode);
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
        translateFn: _t,
        translatableAttributes: ["data-tooltip"],
    });
    return app.mount(document.body);
}
export default { kioskAttendanceApp, createPublicKioskAttendance };
