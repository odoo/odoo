import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component, t, useProps } from "@odoo/owl";

export class BomOverviewDisplayFilter extends Component {
    static template = "mrp.BomOverviewDisplayFilter";
    static components = {
        Dropdown,
        DropdownItem,
    };
    props = useProps({
        showOptions: t.object(),
        changeDisplay: t.function(),
    });

    setup() {
        this.displayOptions = {};
    }

    //---- Getters ----

    get displayableOptions() {
        return Object.keys(this.displayOptions).map(optionKey => ({
            id: optionKey,
            label: this.displayOptions[optionKey],
            onSelected: () => this.props.changeDisplay(optionKey),
            class: { o_menu_item: true, selected: this.props.showOptions[optionKey] },
            closingMode: "none",
        }));
    }
}
