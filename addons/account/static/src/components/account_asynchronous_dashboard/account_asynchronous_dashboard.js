/** @odoo-module **/
import { DashboardKanbanRecord } from '@account/components/bills_upload/bills_upload';
import { useService } from "@web/core/utils/hooks";
const { Component, onMounted, useState } = owl;

export class AccountAsynchronousDashboard extends Component {

    setup() {
        this.orm = useService('orm');
        onMounted(this.fetchData);
        this.state = useState({
            info: {}
        })
    }

    async fetchData() {
        const data = await this.orm.silent.read('account.journal', [this.props.journalId],['kanban_dashboard'], {});
        console.log(this.props);
        this.formatData(data.find((d) => d.id === this.props.journalId));
        console.log('finish');
    }

    get dashboard() {
        return this.state.info;
    }

    formatData(props) {
        this.state.info = JSON.parse(props.kanban_dashboard);
        console.log(this.state.info);
    }

}
AccountAsynchronousDashboard.template = "account.AccountAsynchronousDashboard";

DashboardKanbanRecord.components = {
    ...DashboardKanbanRecord.components,
    AccountAsynchronousDashboard,
};
