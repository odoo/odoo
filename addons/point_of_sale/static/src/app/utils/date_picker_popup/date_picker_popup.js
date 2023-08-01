/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { onMounted, useRef, useState } from "@odoo/owl";

export class DatePickerPopup extends AbstractAwaitablePopup {
    static template = "point_of_sale.DatePickerPopup";
    static defaultProps = {
        confirmText: _t("Confirm"),
        cancelText: _t("Discard"),
        title: _t("DatePicker"),
    };

    setup() {
        super.setup();
        this.state = useState({ shippingDate: this._today() });
        this.inputRef = useRef("input");
        onMounted(() => this.inputRef.el.focus());
    }
    getPayload() {
        return this.state.shippingDate < this._today() ? this._today() : this.state.shippingDate;
    }
    _today() {
        return new Date().toISOString().split("T")[0];
    }
}
