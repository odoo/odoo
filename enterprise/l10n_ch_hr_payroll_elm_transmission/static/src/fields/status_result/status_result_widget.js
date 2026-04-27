/** @odoo-module **/

import { registry } from "@web/core/registry";
import {Component, onWillUpdateProps, useState} from "@odoo/owl";
import { SwissdecNotification } from "@l10n_ch_hr_payroll_elm_transmission/components/swissdec_notification";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class StatusResultWidget extends Component {
    static props = {
        ...standardFieldProps
    }
    static template = "l10n_ch_hr_payroll_elm_transmission.StatusResultWidgetTemplate";
    static components = {
        SwissdecNotification,
    };

    setup() {

        this.state = useState({
            parsedData: this.props.record.data[this.props.name],
        });
        onWillUpdateProps((nextProps) => {
            this.state.parsedData = nextProps.record.data[this.props.name];
        })
    }
}

registry.category("fields").add("swissdec_status_result", {
    component: StatusResultWidget,
});

export default StatusResultWidget;
