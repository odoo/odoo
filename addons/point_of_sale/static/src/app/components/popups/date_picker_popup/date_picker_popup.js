import { Dialog } from "@web/core/dialog/dialog";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, useState } from "@odoo/owl";
const { DateTime } = luxon;

export class DatePickerPopup extends Component {
    static template = "point_of_sale.DatePickerPopup";
    static components = { Dialog, DateTimeInput };
    static props = {
        title: { type: String, optional: true },
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
        this.state = useState({
            shippingDate: DateTime.now(),
        });
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
        this.state.shippingDate = date;
    }
    confirm() {
        const selected = this.state.shippingDate.toISODate();
        this.props.getPayload(selected);
        this.props.close();
    }
}
