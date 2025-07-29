import { BaseOptionComponent, useGetItemValue } from "@html_builder/core/utils";

export class SearchbarOption extends BaseOptionComponent {
    static template = "website.SearchbarOption";
    static selector = ".s_searchbar_input";
    static applyTo = ".search-query";

    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();

        this.orderByItems = this.getResource("searchbar_option_order_by_items");
        this.displayItems = this.getResource("searchbar_option_display_items");
    }
}
