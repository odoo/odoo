import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { DuplicateWebsiteDialog } from "@website/components/dialog/duplicate_website_dialog";

export class WebsiteListController extends listView.Controller {
    /**
     * Asks for the name of the duplicated websites.
     *
     * @override
     */
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        menuItems.duplicate.callback = async () => {
            this.dialogService.add(DuplicateWebsiteDialog, {
                websiteIds: await this.model.root.getResIds(true),
                onDuplicate: () => this.model.load(),
            });
        };
        return menuItems;
    }
}

export const WebsiteListView = {
    ...listView,
    Controller: WebsiteListController,
};

registry.category("views").add("website_list", WebsiteListView);
