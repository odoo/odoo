import { AccordionItem, ACCORDION } from "@web/core/dropdown/accordion_item";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component, useState, useChildSubEnv } from "@odoo/owl";

export class PropertiesGroupByItem extends Component {
    static template = "web.PropertiesGroupByItem";
    static components = { AccordionItem, CheckboxItem, DropdownItem };
    static props = {
        item: Object,
        onGroup: Function,
    };

    setup() {
        this.state = useState({ groupByItems: [] });
        useChildSubEnv({
            [ACCORDION]: {
                accordionStateChanged: this.beforeOpen.bind(this),
            },
        });
    }

    /**
     * The properties field is considered as active if one of its property is active.
     */
    get isActive() {
        return this.state.groupByItems.some((item) => item.isActive);
    }

    /**
     * True if all group items come from the same definition record.
     */
    get isSingleParent() {
        const uniqueNames = new Set(this.state.groupByItems.map((item) => item.definitionRecordId));
        return uniqueNames.size < 2;
    }

    /**
     * Dynamically load the definition, only when needed (if we open the dropdown).
     */
    async beforeOpen() {
        if (this.definitionLoaded) {
            return;
        }
        this.definitionLoaded = true;

        await this.env.searchModel.fillSearchViewItemsProperty();
        this._updateGroupByItems();
    }

    /**
     * Callback to group records per one property.
     */
    onGroup(ids) {
        this.props.onGroup(ids);
        this._updateGroupByItems(); // isActive state might have changed
    }

    /**
     * Update the component state to sync it with the search model group item.
     */
    _updateGroupByItems() {
        this.state.groupByItems = this.env.searchModel.getSearchItems(
            (searchItem) =>
                ["groupBy", "dateGroupBy"].includes(searchItem.type) &&
                searchItem.isProperty &&
                searchItem.propertyFieldName === this.props.item.fieldName
        );
    }
}
