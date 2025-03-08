import {PageControllerMixin} from "./page_views_mixin";
import {PageSearchModel} from "./page_search_model";
import {registry} from '@web/core/registry';
import {kanbanView} from "@web/views/kanban/kanban_view";

export class PageKanbanController extends PageControllerMixin(kanbanView.Controller) {
    static components = {
        ...kanbanView.Controller.components,
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
