import { onWillStart } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";

import { EmployeeOnboarding } from "./employee_onboarding_view";
import { getEmployeeHelper } from "@hr/core/common/onboarding/employee_onboarding_helper";
import { useArchiveEmployee } from "./archive_employee_hook";

export class EmployeeListController extends ListController {
    setup() {
        super.setup();
        this.archiveEmployee = useArchiveEmployee();
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        const selectedRecords = this.model.root.selection;

        menuItems.archive.callback = this.archiveEmployee.bind(
            this,
            selectedRecords.map(({ resId }) => resId)
        );
        return menuItems;
    }

    async createRecord() {
        await this.props.createRecord();
    }
}

export class EmployeeListRenderer extends ListRenderer {
    static template = "hr.EmployeeListRenderer";
    static components = {
        ...ListRenderer.components,
        EmployeeOnboarding,
    };

    setup() {
        super.setup();
        this.state.helper = null;
        this.orm = useService("orm");
        onWillStart(async () => {
            this.state.helper = await getEmployeeHelper(this.orm);
        });
    }

    get _employeeNames() {
        return this.env.model.root.records.map((record) => record.data.name);
    }

    get _isSearching() {
        return this.env.searchModel.searchDomain?.length > 1;
    }

    get showOnboarding() {
        const state = this.state.helper.getState(this._employeeNames, this._isSearching);
        return !(state.notOnboarding || state.hideHelper);
    }

    get showLoadSample() {
        return this.state.helper.getState(this._employeeNames, this._isSearching).showLoadSample;
    }

    get showNoContentHelper() {
        if (this.showOnboarding) {
            return false;
        }
        return super.showNoContentHelper;
    }
}

registry.category("views").add("hr_employee_list", {
    ...listView,
    Renderer: EmployeeListRenderer,
    Controller: EmployeeListController,
});
