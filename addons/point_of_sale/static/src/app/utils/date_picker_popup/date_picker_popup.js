/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, useRef, useState } from "@odoo/owl";

export class DatePickerPopup extends Component {
    static template = "point_of_sale.DatePickerPopup";
    static components = { Dialog };
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
    confirm() {
        this.props.getPayload(
            this.state.shippingDate < this._today() ? this._today() : this.state.shippingDate
        );
        this.props.close();
    }
    _today() {
        return new Date().toISOString().split("T")[0];
    }
}
