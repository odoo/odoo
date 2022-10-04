/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart } = owl;

export class JournalDashboardValues extends Component {

    setup() {
        this.orm = useService('orm');
        onWillStart(this.fetchData);
    }

    async fetchData() {
        const data = await this.orm.read(this.props.record.model, [this.props.record.resId],['json_activity_data'], {});
        this.formatData(data)
    }

    formatData(props) {
        this.info = JSON.parse(props);
    }

}
JournalDashboardValues.template = "account.JournalDashboardValues";

registry.category("fields").add("kanban_vat_activity", JournalDashboardValues);
