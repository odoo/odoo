import { Component, proxy, useProps, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class DailySalesReportPopup extends Component {
    static template = "pos_hr.DailySalesReportPopup";
    static components = { Dialog };
    props = useProps({
        getPayload: t.function(),
        close: t.function(),
    });

    setup() {
        this.state = proxy({ includeEmployees: true });
    }

    confirm() {
        this.props.getPayload(this.state.includeEmployees);
        this.props.close();
    }
}
