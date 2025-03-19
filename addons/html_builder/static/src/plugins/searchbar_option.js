import {
    useBuilderComponents,
    useDomState,
    useGetItemValue,
    useIsActiveItem,
} from "@html_builder/core/utils";
import { Component } from "@odoo/owl";

export class SearchbarOption extends Component {
    static template = "html_builder.SearchbarOption";
    static props = {
        getOrderByItems: Function,
        getDisplayItems: Function,
    };

    setup() {
        useBuilderComponents();
        this.isActiveItem = useIsActiveItem();
        this.getItemValue = useGetItemValue();

        this.state = useDomState(() => ({
            orderByItems: this.props.getOrderByItems(),
            displayItems: this.props.getDisplayItems(),
        }));
    }
}
