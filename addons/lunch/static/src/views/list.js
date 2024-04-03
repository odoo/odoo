/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { registry } from '@web/core/registry';

import { listView } from '@web/views/list/list_view';
import { ListRenderer } from '@web/views/list/list_renderer';

import { LunchDashboard } from '../components/lunch_dashboard';
import { LunchRendererMixin } from '../mixins/lunch_renderer_mixin';

import { LunchSearchModel } from './search_model';


export class LunchListRenderer extends ListRenderer {
    onCellClicked(record, column) {
        this.openOrderLine(record.resId);
    }
}
patch(LunchListRenderer.prototype, 'lunch_list_renderer_mixin', LunchRendererMixin);

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
