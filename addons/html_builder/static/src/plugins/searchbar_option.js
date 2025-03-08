import {
    useDomState,
    useGetItemValue,
    useIsActiveItem,
} from "@html_builder/core/building_blocks/utils";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component } from "@odoo/owl";

export class SearchbarOption extends Component {
    static template = "html_builder.SearchbarOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        getOrderByItems: Function,
        getDisplayItems: Function,
    };

    setup() {
        this.isActiveItem = useIsActiveItem();
        this.getItemValue = useGetItemValue();

        this.state = useDomState(() => ({
            orderByItems: this.props.getOrderByItems(),
            displayItems: this.props.getDisplayItems(),
        }));
    }
}
