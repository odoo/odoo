/** @odoo-module */

import { registry } from '@web/core/registry';

import { listView } from '@web/views/list/list_view';
import { ListRenderer } from '@web/views/list/list_renderer';

import { LunchDashboard } from '../components/lunch_dashboard';
import { LunchRendererMixin } from '../mixins/lunch_renderer_mixin';

import { LunchSearchModel } from './search_model';


export class LunchListRenderer extends LunchRendererMixin(ListRenderer) {
    onCellClicked(record, column) {
        this.openOrderLine(record.resId);
    }
}

LunchListRenderer.template = 'lunch.ListRenderer';
LunchListRenderer.components = {
    ...LunchListRenderer.components,
    LunchDashboard,
}

registry.category('views').add('lunch_list', {
    ...listView,
    Renderer: LunchListRenderer,
    SearchModel: LunchSearchModel,
});
