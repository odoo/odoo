/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { BarcodeScanner } from "@barcodes/components/barcode_scanner";
import { Component, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { EventRegistrationSummaryDialog } from "./event_registration_summary_dialog";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export class EventScanView extends Component {
    static template = "event.EventScanView";
    static components = { BarcodeScanner };
    static props = { ...standardActionServiceProps };

    setup() {
        this.actionService = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm");

        const { default_event_id, active_model, active_id } = this.props.action.context;
        this.eventId = default_event_id || (active_model === "event.event" && active_id);
        this.isMultiEvent = !this.eventId;

        const barcode = useService("barcode");
        useBus(barcode.bus, "barcode_scanned", (ev) => this.onBarcodeScanned(ev.detail.barcode));

        onWillStart(this.onWillStart);
    }

    /**
     * @override
     * Fetch barcode init information. Notably eventId triggers mono- or multi-
     * event mode (Registration Desk in multi event allow to manage attendees
     * from several events and tickets without reloading / changing event in UX.
     */
    async onWillStart() {
        this.data = await rpc("/event/init_barcode_interface", {
            event_id: this.eventId,
        });
    }

    /**
     * When scanning a barcode, call Registration.register_attendee() to get
     * formatted registration information, notably its status or event-related
     * information. Open a confirmation / choice Dialog to confirm attendee.
     */
    async onBarcodeScanned(barcode) {
        const result = await this.orm.call("event.registration", "register_attendee", [], {
            barcode: barcode,
            event_id: this.eventId,
        });

        if (result.error && result.error === "invalid_ticket") {
            this.notification.add(_t("Invalid ticket"), {
                title: _t("Warning"),
                type: "danger",
            });
        } else {
            this.registrationId = result.id;
            this.closeLastDialog?.();
            this.closeLastDialog = this.dialog.add(EventRegistrationSummaryDialog, {
                registration: result
            });
        }
    }

    onClickSelectAttendee() {
        if (this.isMultiEvent) {
            this.actionService.doAction("event.event_registration_action");
        } else {
            this.actionService.doAction("event.event_registration_action_kanban", {
                additionalContext: {
                    active_id: this.eventId,
                    search_default_unconfirmed: true,
                    search_default_confirmed: true,
                },
            });
        }
    }

    onClickBackToEvents() {
        if (this.isMultiEvent) {
            this.actionService.doAction("event.action_event_view", {
                clearBreadcrumbs: true,
            });
        } else {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "event.event",
                res_id: this.eventId,
                views: [[false, "form"]],
                target: "main",
            });
        }
    }
}

registry.category("actions").add("event.event_barcode_scan_view", EventScanView);
