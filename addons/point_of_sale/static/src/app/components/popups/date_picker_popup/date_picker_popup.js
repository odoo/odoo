import { Dialog } from "@web/core/dialog/dialog";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
const { DateTime } = luxon;

export class DatePickerPopup extends Component {
    static template = "point_of_sale.DatePickerPopup";
    static components = { Dialog, DateTimeInput };
    static props = {
        title: { type: String, optional: true },
        defaultValue: { type: DateTime, optional: true },
        confirmLabel: { type: String, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        confirmLabel: _t("Confirm"),
        title: _t("DatePicker"),
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.state = useState({ shippingDate: this.props.defaultValue ?? DateTime.now() });
        onMounted(() => {
            const input = document.querySelector(".shipping-date-selector input");
            if (input) {
                input.classList.remove("o_input");
                input.classList.add("form-control", "form-control-lg");
                input.focus();
            }
        });
    }
    onDateChange(date) {
        const today = DateTime.now().startOf("day");
        if (date && date < today) {
            this.dialog.add(AlertDialog, {
                title: _t("Validation Error"),
                body: _t("Selected date cannot be in the past."),
            });
            this.state.shippingDate = today;
        } else {
            this.state.shippingDate = date;
        }
    }
    confirm() {
        this.props.getPayload(this.state.shippingDate);
        this.props.close();
    }
}
