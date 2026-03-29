/** @odoo-module */
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

export class LabDashBoard extends Component {
    static template = "LabDashboard";

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.user = user;
        this.actionService = useService("action");
        this.state = useState({
            tests_confirm: [],
            tests_confirm_data: [],
            test_data: [],
            all_test_data: [],
            process_data: [],
            process_test_data: [],
            published_data: [],
            activeView: 'main',
            showCreateButton: true,
        });

        onMounted(async () => {
            await this._loadTestData();
        });
    }

    // Method for loading lab test data
    async _loadTestData() {
        this.state.activeView = 'main';
        this.state.showCreateButton = true;
        const domain = [['state', '=', 'draft']];
        const result = await this.orm.call('lab.test.line', 'search_read', [domain]);
        this.state.tests_confirm = result;
    }

    // Method for handling click on tests to confirm
    async _fetchTestData(ev) {
        this.state.activeView = 'form';
        this.state.showCreateButton = false;
        const recordId = parseInt(ev.currentTarget.dataset.index);
        this.recordId = recordId;
        const result = await this.orm.call('lab.test.line', 'action_get_patient_data', [this.recordId]);
        this.state.tests_confirm_data = result;
        this.state.test_data = result['test_data'];
    }

    // Method for confirming lab test
    async confirmLabTest() {
        try {
            await this.orm.call('lab.test.line', 'create_lab_tests', [this.recordId]);
            this.state.showCreateButton = false;
            alert('The test has been confirmed');
            await this._loadTestData();
        } catch (error) {
            console.error('Error confirming lab test:', error);
            alert('Failed to confirm the test');
        }
    }

    // Method for fetching all lab tests
    async _allLabTest() {
        this.state.activeView = 'process';
        this.state.showCreateButton = false;
        const result = await this.orm.call('patient.lab.test', 'search_read', []);
        const filtered = result.filter(record => record.state !== 'completed');
        this.state.all_test_data = filtered;
    }

    // Method for fetching all test data
    async fetch_all_test_data(ev) {
        const recordId = parseInt(ev.currentTarget.dataset.index);
        await this.load_all_test_data(recordId);
    }

    // Method for loading all test data
    async load_all_test_data(recordId) {
        return await this.actionService.doAction({
            name: _t('Inpatient details'),
            type: 'ir.actions.act_window',
            res_model: 'patient.lab.test',
            res_id: recordId,
            views: [[false, "form"]],
        });
    }

    // Method for loading published lab tests
    async _loadPublished() {
        this.state.activeView = 'published';
        this.state.showCreateButton = false;
        const result = await this.orm.call('lab.test.result', 'print_test_results', []);
        this.state.published_data = result;
    }
}

registry.category("actions").add('lab_dashboard_tags', LabDashBoard);
