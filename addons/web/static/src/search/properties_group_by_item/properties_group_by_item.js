// @ts-check

/** @module @web/search/properties_group_by_item/properties_group_by_item - Group-by dropdown item that lazily loads property definitions for grouping */

import { Component, useChildSubEnv, useState } from "@odoo/owl";
import { ACCORDION, AccordionItem } from "@web/components/dropdown/accordion_item";
import { CheckboxItem } from "@web/components/dropdown/checkbox_item";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
/**
 * Group-by dropdown item for model properties fields.
 * Lazily loads property definitions on first open, then displays
 * sub-items for each property that supports grouping.
 */
export class PropertiesGroupByItem extends Component {
    static template = "web.PropertiesGroupByItem";
    static components = { AccordionItem, CheckboxItem, DropdownItem };
    static props = {
        item: Object,
        onGroup: Function,
    };

    /** Initialize reactive state and register the accordion open callback. */
    setup() {
        /** @type {{ groupByItems: Array<Object> }} */
        this.state = useState({ groupByItems: [] });
        /** @type {boolean} */
        this.definitionLoaded = false;
        useChildSubEnv({
            [ACCORDION]: {
                accordionStateChanged: this.beforeOpen.bind(this),
            },
        });
    }

    /**
     * The properties field is considered as active if one of its property is active.
     * @returns {boolean}
     */
    get isActive() {
        return this.state.groupByItems.some((item) => item.isActive);
    }

    /**
     * True if all group items come from the same definition record.
     * @returns {boolean}
     */
    get isSingleParent() {
        const uniqueNames = new Set(
            this.state.groupByItems.map((item) => item.definitionRecordId),
        );
        return uniqueNames.size < 2;
    }

    /**
     * Dynamically load the definition, only when needed (if we open the dropdown).
     * @returns {Promise<void>}
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
     * @param {number[]} ids - Search item IDs to activate for grouping.
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
                searchItem.propertyFieldName === this.props.item.fieldName,
        );
    }
}
