/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useService } from "@web/core/utils/hooks";

export class MrpEmployeeListController extends ListController {
    static props = {
        ...ListController.props,
        selectEmployee: { type: Function, optional: true },
        header: { type: Boolean, optional: true },
        footer: { type: Boolean, optional: true },
    };

    async openRecord(record) {
        this.props.selectEmployee(record.data.id);
    }
}

export class MrpEmployeeControlPanel extends ControlPanel {
    static template = "mrp_workorder.MrpEmployeeControlPanel";
    static props = {
        ...ControlPanel.props,
    };

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    }
    dismiss() {
        this.dialogService.closeAll();
    }
}

export class MrpEmployeeListRenderer extends ListRenderer {
    static template = "mrp_workorder.MrpEmployeeListRenderer";
}

export const mrpEmployeeListView = {
    ...listView,
    ControlPanel: MrpEmployeeControlPanel,
    Controller: MrpEmployeeListController,
    Renderer: MrpEmployeeListRenderer,
    props() {
        const props = listView.props(...arguments);
        props.allowSelectors = false;
        return props;
    },
};

registry.category("views").add("mrp_employee_tree", mrpEmployeeListView);
