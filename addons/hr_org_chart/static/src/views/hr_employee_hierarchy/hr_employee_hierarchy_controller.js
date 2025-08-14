import { onWillStart, useState } from "@odoo/owl";
import { HierarchyController } from "@web_hierarchy/hierarchy_controller";
import { useService } from "@web/core/utils/hooks";
import { getEmployeeHelper } from "@hr/core/common/onboarding/employee_onboarding_helper";

export class HrEmployeeHierarchyController extends HierarchyController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({ helper: null });
        onWillStart(async () => {
            this.state.helper = await getEmployeeHelper(this.orm);
        });
    }

    get employeeNames() {
        return this.model.root.rootNodes.map((node) => node.data.name);
    }

    get showOnboarding() {
        const isSearching = this.env.searchModel.searchDomain?.length > 1;
        const state = this.state.helper.getState(this.employeeNames, isSearching);
        return !(state.notOnboarding || state.hideHelper);
    }

    get displayNoContent() {
        if (this.showOnboarding) {
            return false;
        }
        return super.displayNoContent;
    }
}
