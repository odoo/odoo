// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { formatDate } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { NumericInput } from "@point_of_sale/app/components/inputs/numeric_input/numeric_input";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class EventSlotSelectionPopup extends Component {
    static template = "pos_event.EventSlotSelectionPopup";
    static props = ["getPayload", "close", "event"];
    static components = {
        Dialog,
        ProductCard,
        NumericInput,
    };
    setup() {
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
        this.props.event.slot_ids.forEach((slot) => {
            const date = formatDate(slot.date, { format: "MMM dd yyyy, EEEE" });
            if (!slots[date]) {
                slots[date] = {};
            }
            slots[date][slot.id] = slot.start_datetime.toFormat(
                localization.timeFormat.replace(":ss", "")
            );
        });
        return slots;
    }
    select(ev) {
        this.slotId = parseInt(ev.currentTarget.dataset.slotId);
        // Visually select the button
        document.querySelectorAll(".o_event_slot_btn").forEach((btn) => {
            btn.classList.replace("btn-primary", "btn-secondary");
        });
        ev.currentTarget.classList.replace("btn-secondary", "btn-primary");
        // Update selected slot display
        const selectedSlot = this.props.event.slot_ids.filter((slot) => slot.id == this.slotId);
        if (selectedSlot.length) {
            this.state.selectedSlotDisplay = selectedSlot[0].start_datetime.toFormat(
                "MMM dd yyyy, EEEE, h:mm a"
            );
        }
    }
    confirm() {
        if (!this.slotId) {
            this.dialog.add(AlertDialog, {
                title: "Error",
                body: "Please select a slot",
            });
            return;
        }
        this.props.getPayload(this.slotId);
        this.props.close();
    }
    cancel() {
        this.props.close();
    }
}
