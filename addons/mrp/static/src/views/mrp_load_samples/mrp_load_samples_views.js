import { onWillStart, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ActionHelper } from "@web/views/action_helper";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";

export class MrpLoadSamplesActionHelper extends ActionHelper {
    static template = "mrp.MrpLoadSamplesActionHelper";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.resModel = this.env.searchModel.resModel;
        this.state = proxy({ canLoadSamples: false });
        onWillStart(async () => {
            this.state.canLoadSamples = await this.orm.call(this.resModel, "can_load_samples", [
                [],
            ]);
        });
    }

    async loadSamples() {
        this.state.canLoadSamples = "disabled";
        await this.orm.call(this.resModel, "action_load_samples", [[]]);
        this.state.canLoadSamples = false;
        await this.env.model.load();
    }
}

export class MrpLoadSamplesListRenderer extends ListRenderer {
    static components = {
        ...ListRenderer.components,
        ActionHelper: MrpLoadSamplesActionHelper,
    };
}

registry.category("views").add("mrp_load_samples_list", {
    ...listView,
    Renderer: MrpLoadSamplesListRenderer,
});

export class MrpLoadSamplesKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        ActionHelper: MrpLoadSamplesActionHelper,
    };
}

registry.category("views").add("mrp_load_samples_kanban", {
    ...kanbanView,
    Renderer: MrpLoadSamplesKanbanRenderer,
});
