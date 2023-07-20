/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component, useRef, useState } from "@odoo/owl";

export class HierarchyNavbar extends Component {
    setup() {
        this.searchInput = useRef("search");
        this.websiteNamesState = useState(Array.from(this.props.websites.names));
    }

    get websiteNames() {
        return this.websiteNamesState.map((websiteName) => ({
            label: websiteName,
            onSelected: () => this.props.selectWebsite(websiteName),
        }));
    }

    /**
     * @param {Event} event
     */
    onInputKeydown(event) {
        if (event.key === "Enter" || event.key === "Tab") {
            event.preventDefault();
            this.props.searchView(event.target.value, !event.shiftKey);
        }
    }

    /**
     * @param {Event} event
     */
    onInputClick(event) {
        this.props.searchView(this.searchInput.el.value, !event.shiftKey);
    }
}

HierarchyNavbar.components = {
    Dropdown,
    DropdownItem,
};
HierarchyNavbar.template = "website.hierarchy_navbar";
HierarchyNavbar.props = {
    toggleInactive: Function,
    websites: Object,
    selectWebsite: Function,
    searchView: Function,
};
