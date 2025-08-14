import { onWillStart } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanController } from "@web/views/kanban/kanban_controller";

import { getEmployeeHelper } from "@hr/core/common/onboarding/employee_onboarding_helper";
import { EmployeeOnboarding } from "./employee_onboarding_view";
import { useArchiveEmployee } from "./archive_employee_hook";
import { OnboardingHelperBlocks } from "./onboarding/onboarding_helper_blocks";

export class EmployeeKanbanController extends KanbanController {
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
}

export class EmployeeKanbanRenderer extends KanbanRenderer {
    static template = "hr.EmployeeKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        EmployeeOnboarding,
        OnboardingHelperBlocks,
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

registry.category("views").add("hr_employee_kanban", {
    ...kanbanView,
    Renderer: EmployeeKanbanRenderer,
    Controller: EmployeeKanbanController,
});
