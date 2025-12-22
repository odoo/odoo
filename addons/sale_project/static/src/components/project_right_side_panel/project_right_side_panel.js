import { patch } from "@web/core/utils/patch";
import { ProjectRightSidePanel } from '@project/components/project_right_side_panel/project_right_side_panel';

patch(ProjectRightSidePanel.prototype, {

    get panelVisible() {
        return super.panelVisible || this.state.data.show_sale_items;
    },
});
