import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

import { getEmployeeHelper } from "@hr/core/common/onboarding/employee_onboarding_helper";
import { HierarchyRenderer } from "@web_hierarchy/hierarchy_renderer";
import { HrEmployeeHierarchyCard } from "./hr_employee_hierarchy_card";
import { EmployeeOnboarding } from "@hr/views/employee_onboarding_view";

export class HrEmployeeHierarchyRenderer extends HierarchyRenderer {
    static template = "hr_org_chart.HrEmployeeHierarchyRenderer";
    static components = {
        ...HierarchyRenderer.components,
        EmployeeOnboarding,
        HierarchyCard: HrEmployeeHierarchyCard,
        Avatar,
    };

    setup() {
        super.setup();
        this.state = useState({ helper: null });
        this.orm = useService("orm");
        onWillStart(async () => {
            this.state.helper = await getEmployeeHelper(this.orm);
        });
    }

    get _employeeNames() {
        return this.props.model.root.rootNodes.map((node) => node.data.name);
    }

    get _isSearching() {
        return this.env.searchModel.searchDomain?.length > 1;
    }

    get showLoadSample() {
        return this.state.helper.getState(this._employeeNames, this._isSearching).showLoadSample;
    }

    get showOnboarding() {
        const state = this.state.helper.getState(this._employeeNames, this._isSearching);
        return !(state.notOnboarding || state.hideHelper);
    }
}
