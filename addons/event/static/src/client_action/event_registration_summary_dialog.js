import { Component, onMounted, useState, useRef } from "@odoo/owl";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { uuid } from "@web/views/utils";
import { _t } from "@web/core/l10n/translation";

const IOT_BOX_PING_TIMEOUT_MS = 1000;
const PRINT_SETTINGS_LOCAL_STORAGE_KEY = "event.registration_print_settings";
const DEFAULT_PRINT_SETTINGS = {
    autoPrint: false,
    iotPrinterId: null
};

export class EventRegistrationSummaryDialog extends Component {
    static template = "event.EventRegistrationSummaryDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        doNextScan: { type: Function, optional: true },
        model: { type: Object, optional: true },
        playSound: { type: Function, optional: true },
        registration: { type: Object },
    };

    setup() {
        this.actionService = useService("action");
        this.isBarcodeScannerSupported = isBarcodeScannerSupported();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.continueButtonRef = useRef("continueButton");
        this.button = useState({enabled: true});

        this.registrationStatus = useState({value: this.registration.status});
        const storedPrintSettings = browser.localStorage.getItem(PRINT_SETTINGS_LOCAL_STORAGE_KEY);
        this.printSettings = useState(storedPrintSettings ? JSON.parse(storedPrintSettings) : DEFAULT_PRINT_SETTINGS);
        this.useIotPrinter = this.registration.iot_printers.length > 0;

        if (this.useIotPrinter && !this.registration.iot_printers.map(printer => printer.id).includes(this.printSettings.iotPrinterId)) {
            this.printSettings.iotPrinterId = null;
        }

        if (this.registration.iot_printers.length === 1) {
            this.printSettings.iotPrinterId = this.registration.iot_printers[0].id;
        }

        this.dialogState = useState({ isHidden: this.willAutoPrint });

        onMounted(() => {
            if (['already_registered', 'need_manual_confirmation'].includes(this.props.registration.status) && this.props.playSound) {
                this.props.playSound("notify");
            } else if (['not_ongoing_event', 'canceled_registration'].includes(this.props.registration.status) && this.props.playSound) {
                this.props.playSound("error");
            } else if (this.willAutoPrint) {
                this.onRegistrationPrintPdf()
                    .catch(() => { this.dialogState.isHidden = false; });
            }
            // Without this, repeat barcode scans don't work as focus is lost
            this.continueButtonRef.el?.focus();
        });
    }

    get registration() {
        return this.props.registration;
    }

    get selectedPrinter() {
        return this.registration.iot_printers.find(printer => printer.id === this.printSettings.iotPrinterId);
    }

    get needManualConfirmation() {
        return this.registrationStatus.value === "need_manual_confirmation";
    }

    get willAutoPrint() {
        return (
            this.registration.status === "confirmed_registration" &&
            this.printSettings.autoPrint &&
            this.useIotPrinter &&
            this.hasSelectedPrinter()
        );
    }

    async onRegistrationConfirm() {
        if (this.registrationStatus.value !== "confirmed_registration") {
            this.button.enabled = false
            await this.orm.call("event.registration", "action_set_done", [this.registration.id]).catch(() => this.button.enabled = true);
            this.registrationStatus.value = "confirmed_registration";
        }
        this.props.close();
        if (this.props.model) {
            this.props.model.load();
        }
        if (this.props.doNextScan) {
            this.onScanNext();
        }
    }

    async undoRegistration() {
        if (["confirmed_registration", "already_registered"].includes(this.registrationStatus.value)) {
            await this.orm.call("event.registration", "action_confirm", [this.registration.id]);
        } else if (this.registrationStatus.value == "unconfirmed_registration") {
            await this.orm.call("event.registration", "action_set_draft", [this.registration.id]);
        }
        this.props.close();
        if (this.props.model) {
            this.props.model.load();
        }
    }

    async onRegistrationPrintPdf() {
        if (this.useIotPrinter && this.printSettings.iotPrinterId) {
            await this.printWithBadgePrinter();
        } else {
            await this.actionService.doAction({
                type: "ir.actions.report",
                report_type: "qweb-pdf",
                report_name: `event.event_registration_report_template_badge/${this.registration.id}`,
            });
        }
        if (this.props.doNextScan) {
            this.onScanNext();
        } else {
            this.dialogState.isHidden = false;
        }
    }

    async onRegistrationView() {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "event.registration",
            res_id: this.registration.id,
            views: [[false, "form"]],
            target: "current",
        });
        this.props.close();
    }

    async onScanNext() {
        this.props.close();
        if (this.isBarcodeScannerSupported) {
            this.props.doNextScan();
        }
    }

    hasSelectedPrinter() {
        return !this.useIotPrinter || this.printSettings.iotPrinterId != null;
    }

    savePrintSettings() {
        browser.localStorage.setItem(PRINT_SETTINGS_LOCAL_STORAGE_KEY, JSON.stringify(this.printSettings));
    }

    async isIotBoxReachable() {
        const timeoutController = new AbortController();
        setTimeout(() => timeoutController.abort(), IOT_BOX_PING_TIMEOUT_MS);
        const iotBoxUrl = this.selectedPrinter?.ipUrl;

        try {
            const response = await browser.fetch(`${iotBoxUrl}/hw_proxy/hello`, { signal: timeoutController.signal });
            return response.ok;
        } catch {
            return false;
        }
    }

    async printWithLongpolling(reportId) {
        try {
            const [[ip, identifier,, printData]] = await this.orm.call("ir.actions.report", "render_and_send", [
                reportId,
                [this.selectedPrinter],
                [this.registration.id],
                null,
                null,
                false, // Do not use websocket
            ]);
            const payload = { document: printData, print_id: uuid() }
            const { result } = await this.env.services.iot_longpolling.action(ip, identifier, payload, true);
            return result;
        } catch {
            return false;
        }
    }

    async printWithBadgePrinter() {
        const reportName = `event.event_report_template_esc_label_${this.registration.badge_format}_badge`;
        const [{ id: reportId }] = await this.orm.searchRead("ir.actions.report", [["report_name", "=", reportName]], ["id"]);
        const ticket_type = this.registration.ticket_name ? this.registration.ticket_name : '';

        this.notification.add(
            _t("'%(name)s' %(type)s badge sent to printer '%(printer)s'", {
                name: this.registration.name,
                type: ticket_type,
                printer: this.selectedPrinter.name,
            }),
            { type: "info" }
        );
        if (await this.isIotBoxReachable()) {
            const printSuccessful = await this.printWithLongpolling(reportId);
            if (printSuccessful) {
                return;
            }
        }
        const printJobArguments = [reportId, [this.registration.id], null, uuid()];
        await this.env.services.iot_websocket.addJob([this.printSettings.iotPrinterId], printJobArguments);
    }
}
