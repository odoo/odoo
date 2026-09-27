import { registry } from '@web/core/registry';

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanRecord } from '@web/views/kanban/kanban_record';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { KanbanController } from '@web/views/kanban/kanban_controller';

import { LunchDashboard } from '../components/lunch_dashboard';
import { LunchRendererMixin } from '../mixins/lunch_renderer_mixin';

import { LunchSearchModel } from './search_model';
import { LunchSearchPanel } from './search_panel';

export class LunchKanbanRecord extends KanbanRecord {
    onGlobalClick(ev) {
        this.env.bus.trigger('lunch_open_order', {productId: this.props.record.resId});
    }
}

export class LunchKanbanRenderer extends LunchRendererMixin(KanbanRenderer) {
    static template = "lunch.KanbanRenderer";
    static components = {
        ...LunchKanbanRenderer.components,
        LunchDashboard,
        KanbanRecord: LunchKanbanRecord,
    };

    getGroupsOrRecords() {
        const { locationId } = this.env.searchModel.lunchState;
        if (!locationId) {
            return [];
        } else {
            return super.getGroupsOrRecords(...arguments);
        }
    }
}

class LunchKanbanController extends KanbanController {
    get modelOptions() {
        return {
            ...super.modelOptions,
            lazy: false,
        };
    }
}

registry.category('views').add('lunch_kanban', {
    ...kanbanView,
    Controller: LunchKanbanController,
    Renderer: LunchKanbanRenderer,
    SearchModel: LunchSearchModel,
    SearchPanel: LunchSearchPanel,
});
