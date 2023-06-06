/** @odoo-module **/

import {PageControllerMixin, PageRendererMixin} from "./page_views_mixin";
import {registry} from '@web/core/registry';
import {kanbanView} from "@web/views/kanban/kanban_view";
import {SearchDropdownItem} from "@web/search/search_dropdown_item/search_dropdown_item";


export class PageKanbanController extends PageControllerMixin(kanbanView.Controller) {
    /**
     * @override
     */
    async createRecord() {
        return this.createWebsiteContent();
    }
}
PageKanbanController.template = 'website.PageKanbanView';
PageKanbanController.components = {
    ...kanbanView.Controller.components,
    SearchDropdownItem,
};

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
};

registry.category("views").add("website_pages_kanban", PageKanbanView);
