/** @odoo-module */

import { registry } from '@web/core/registry';

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanRecord } from '@web/views/kanban/kanban_record';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';

import { LunchDashboard } from '../components/lunch_dashboard';
import { LunchRendererMixin } from '../mixins/lunch_renderer_mixin';

import { LunchSearchModel } from './search_model';


export class LunchKanbanRecord extends KanbanRecord {
    onGlobalClick(ev) {
        this.env.bus.trigger('lunch_open_order', {productId: this.props.record.resId});
    }
}

export class LunchKanbanRenderer extends LunchRendererMixin(KanbanRenderer) {}

LunchKanbanRenderer.template = 'lunch.KanbanRenderer';
LunchKanbanRenderer.components = {
    ...LunchKanbanRenderer.components,
    LunchDashboard,
    KanbanRecord: LunchKanbanRecord,
}

registry.category('views').add('lunch_kanban', {
    ...kanbanView,
    Renderer: LunchKanbanRenderer,
    SearchModel: LunchSearchModel,
});
