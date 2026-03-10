/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class DailySalesReportPopup extends Component {
    static template = "pos_hr.DailySalesReportPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        size: { type: String, optional: true },
        closePopup: { type: String, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        closePopup: _t("Discard"),
        title: _t("Daily Sales Report"),
        size: "md",
    };

    setup() {
        this.state = useState({
            add_report_per_employee: true,
        });
    }

    confirm() {
        this.props.getPayload({
            add_report_per_employee: this.state.add_report_per_employee,
        });
        this.props.close();
    }

    onChange(ev) {
        this.state.add_report_per_employee = ev.target.checked;
    }

    cancel() {
        this.props.close();
    }
}
