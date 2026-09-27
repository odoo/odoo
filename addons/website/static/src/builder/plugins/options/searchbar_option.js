import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useGetItemValue } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SearchbarOption extends BaseOptionComponent {
    static id = "searchbar_option";
    static template = "website.SearchbarOption";

    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();
        this.orm = useService("orm");
        this.website = useService("website");

        this.orderByItems = this.getResource("searchbar_option_order_by_items");
        this.searchScopes = [];
        onWillStart(async () => {
            this.searchScopes = await this.orm.cache().call("website", "get_search_scopes", [
                this.website.currentWebsiteId,
            ]);
        });
    }
}

registry.category("website-options").add(SearchbarOption.id, SearchbarOption);
