/** @odoo-module **/

import {PageControllerMixin, PageRendererMixin} from "./page_views_mixin";
import {registry} from '@web/core/registry';
import {kanbanView} from "@web/views/kanban/kanban_view";
import {CheckboxItem} from "@web/core/dropdown/checkbox_item";

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
    CheckboxItem,
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
