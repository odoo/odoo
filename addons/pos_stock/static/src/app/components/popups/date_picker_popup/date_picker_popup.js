import { Dialog } from "@web/core/dialog/dialog";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, props, proxy, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
const { DateTime } = luxon;

export class DatePickerPopup extends Component {
    static template = "pos_stock.DatePickerPopup";
    static components = { Dialog, DateTimeInput };
    props = props({
        title: t.string().optional(_t("DatePicker")),
        defaultValue: t.instanceOf(DateTime).optional(),
        confirmLabel: t.string().optional(_t("Confirm")),
        getPayload: t.function(),
        close: t.function(),
    });

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.state = proxy({ shippingDate: this.props.defaultValue ?? DateTime.now() });
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
