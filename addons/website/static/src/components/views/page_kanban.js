/** @odoo-module **/

import {PageControllerMixin} from "./page_views_mixin";
import {PageSearchModel} from "./page_search_model";
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

export const PageKanbanView = {
    ...kanbanView,
    Controller: PageKanbanController,
    SearchModel: PageSearchModel,
};

registry.category("views").add("website_pages_kanban", PageKanbanView);
