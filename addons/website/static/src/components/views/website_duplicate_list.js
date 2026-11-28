import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { listView } from "@web/views/list/list_view";

export class WebsiteDuplicateListController extends listView.Controller {
    /**
     * Duplicates the selected websites along with their content, after asking
     * for the name of the new websites.
     *
     * @override
     */
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        menuItems.duplicate.isAvailable = () => this.activeActions.duplicate && user.isSystem;
        menuItems.duplicate.callback = () =>
            this.actionService.doAction("website.website_duplicate_action", {
                additionalContext: {
                    active_ids: this.model.root.selection.map((record) => record.resId),
                },
                onClose: () => this.model.load(),
            });
        return menuItems;
    }
}

export const WebsiteDuplicateListView = {
    ...listView,
    Controller: WebsiteDuplicateListController,
};

registry.category("views").add("website_duplicate_list", WebsiteDuplicateListView);
