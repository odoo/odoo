/** @odoo-module **/

import {PageControllerMixin, PageRendererMixin} from "./page_views_mixin";
import {registry} from '@web/core/registry';
import {kanbanView} from "@web/views/kanban/kanban_view";
import {CheckboxItem} from "@web/core/dropdown/checkbox_item";

export class PageKanbanController extends PageControllerMixin(kanbanView.Controller) {
    static template = "website.PageKanbanView";
    static components = {
        ...kanbanView.Controller.components,
        CheckboxItem,
    };
    /**
     * @override
     */
    async createRecord() {
        return this.createWebsiteContent();
    }
}

export class PageKanbanRenderer extends PageRendererMixin(kanbanView.Renderer) {
    static props = [...kanbanView.Renderer.props, "activeWebsite"];
    static template = "website.PageKanbanRenderer";
}

export const PageKanbanView = {
    ...kanbanView,
    Renderer: PageKanbanRenderer,
    Controller: PageKanbanController,
};

registry.category("views").add("website_pages_kanban", PageKanbanView);
