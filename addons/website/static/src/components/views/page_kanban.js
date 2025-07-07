import { usePageManager } from "./page_manager_hook";
import {PageSearchModel} from "./page_search_model";
import {registry} from '@web/core/registry';
import {kanbanView} from "@web/views/kanban/kanban_view";
import {CheckboxItem} from "@web/core/dropdown/checkbox_item";

export class PageKanbanController extends kanbanView.Controller {
    static template = "website.PageKanbanView";
    static components = {
        ...kanbanView.Controller.components,
        CheckboxItem,
    };

    setup() {
        super.setup();
        this.pageManager = usePageManager({
            resModel: this.props.resModel,
            createAction: this.props.context.create_action,
        });
    }
    /**
     * @override
     */
    async createRecord() {
        return this.pageManager.createWebsiteContent();
    }
}

export const PageKanbanView = {
    ...kanbanView,
    Controller: PageKanbanController,
    SearchModel: PageSearchModel,
};

registry.category("views").add("website_pages_kanban", PageKanbanView);
