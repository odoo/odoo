/** @odoo-module **/

import {PageControllerMixin, PageRendererMixin} from "./page_views_mixin";
import {PageSearchModel} from "./page_search_model";
import {registry} from '@web/core/registry';
import {kanbanView} from "@web/views/kanban/kanban_view";


export class PageKanbanController extends PageControllerMixin(kanbanView.Controller) {
    /**
     * @override
     */
    async createRecord() {
        return this.createWebsiteContent();
    }
}
PageKanbanController.template = 'website.PageKanbanView';

// TODO master: remove `PageRendererMixin` extend, props override and template
export class PageKanbanRenderer extends PageRendererMixin(kanbanView.Renderer) {}
PageKanbanRenderer.props = [
    ...kanbanView.Renderer.props,
    "activeWebsite",
];
PageKanbanRenderer.template = 'website.PageKanbanRenderer';

export const PageKanbanView = {
    ...kanbanView,
    Renderer: PageKanbanRenderer,
    Controller: PageKanbanController,
    SearchModel: PageSearchModel,
};

registry.category("views").add("website_pages_kanban", PageKanbanView);
