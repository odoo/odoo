// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { formatDate } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { NumericInput } from "@point_of_sale/app/components/inputs/numeric_input/numeric_input";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export class EventSlotSelectionPopup extends Component {
    static template = "pos_event.EventSlotSelectionPopup";
    static props = ["getPayload", "close", "event", "availabilityPerSlot"];
    static components = {
        Dialog,
        NumericInput,
    };
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.slotId = false;
        this.state = useState({
            selectedSlotDisplay: "",
        });
    }
    get dialogTitle() {
        return _t("Select a slot for %(event)s", { event: this.props.event.name });
    }
    get slots() {
        const slots = {};
        this.props.event.event_slot_ids.forEach((slot) => {
            if (slot.start_datetime < DateTime.now()) {
                return false;
            }
            const date = formatDate(slot.date, { format: "MMM dd yyyy, EEEE" });
            if (!slots[date]) {
                slots[date] = [];
            }
            slots[date].push({
                availability: this.props.availabilityPerSlot[slot.id],
                slotId: slot.id,
                startDatetime: slot.start_datetime.toFormat(
                    localization.timeFormat.replace(":ss", "")
                ),
            });
        });
        return slots;
    }
    select(ev) {
        this.slotId = parseInt(ev.currentTarget.dataset.slotId);
        const selectedSlot = this.pos.models["event.slot"].get(this.slotId);
        // Return if not available
        if (!selectedSlot || !this.props.availabilityPerSlot[this.slotId]) {
            return;
        }
        // Visually select the button and update displayed datetime
        document.querySelectorAll(".o_event_slot_btn").forEach((btn) => {
            btn.classList.replace("btn-primary", "btn-secondary");
        });
        ev.currentTarget.classList.replace("btn-secondary", "btn-primary");
        this.state.selectedSlotDisplay = selectedSlot.start_datetime.toFormat(
            "MMM dd yyyy, EEEE, h:mm a"
        );
    }
    confirm() {
        if (!this.slotId) {
            this.dialog.add(AlertDialog, {
                title: "Error",
                body: "Please select a slot.",
            });
            return;
        }
        this.props.getPayload({
            slotAvailability: this.props.availabilityPerSlot[this.slotId],
            slotId: this.slotId,
            slotName: this.state.selectedSlotDisplay,
        });
        this.props.close();
    }
    cancel() {
        this.props.close();
    }
}
