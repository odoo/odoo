import { BaseOptionComponent, useGetItemValue } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class SearchbarOption extends BaseOptionComponent {
    static id = "searchbar_option";
    static template = "website.SearchbarOption";

    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();

        this.orderByItems = this.getResource("searchbar_option_order_by_items");
        this.displayItems = this.getResource("searchbar_option_display_items");
    }
}

registry.category("website-options").add(SearchbarOption.id, SearchbarOption);
