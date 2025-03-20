import { BaseOptionComponent, useGetItemValue } from "@html_builder/core/utils";

export class SearchbarOption extends BaseOptionComponent {
    static template = "html_builder.SearchbarOption";
    static props = {
        getOrderByItems: Function,
        getDisplayItems: Function,
    };

    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();

        this.orderByItems = this.props.getOrderByItems();
        this.displayItems = this.props.getDisplayItems();
    }
}
