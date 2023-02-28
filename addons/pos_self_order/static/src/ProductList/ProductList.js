/** @odoo-module */

const { Component, useState } = owl;
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { useAutofocus } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";
import { NavBar } from "../NavBar/NavBar";
/**
 * @typedef {import("@pos_self_order/jsDocTypes").Product} Product
 * @typedef {import("@pos_self_order/jsDocTypes").Order} Order
 * @typedef {import("@pos_self_order/jsDocTypes").CartItem} CartItem
 */
export class ProductList extends Component {
    setup() {
        this.state = useState(this.env.state);
        /**
         * @type {Object}
         * @property {Set<string>} selected_tags
         */
        this.private_state = useState({
            selected_tags: new Set(),
            search_is_focused: false,
            search_input: "",
        });
        this.selfOrder = useSelfOrder();
        this.formatMonetary = formatMonetary;
        useAutofocus({ refName: "searchInput", mobile: true });
        this._ = _;
    }
    filteredProducts = () => {
        // here we only want to return the products
        // that have the selected tags and that match the search input
        return this.props.productList.filter((product) => {
            return (
                this.itemHasAllOfTheTags(product, this.private_state.selected_tags) &&
                this.itemMatchesSearch(product, this.private_state.search_input)
            );
        });
    };

    /**
     * @param {Product} item
     * @param {Set<string>} selected_tags
     * @returns {boolean}
     * @description returns true if the set of selected tags is a subset of the item's tags
     */
    itemHasAllOfTheTags = (item, selected_tags) => {
        return this.setIsSubset(selected_tags, item.tag_list);
    };
    /**
     * @param {Product} item
     * @param {string} search_input
     * @returns {boolean}
     * @description returns true if the item matches the search input
     */
    itemMatchesSearch = (item, search_input) => {
        // TODO: maybe there is a smarter function we could use here
        if (!search_input) {
            return true;
        }
        return (
            item.name.toLowerCase().includes(search_input.toLowerCase()) ||
            (item.description_sale &&
                item.description_sale.toLowerCase().includes(search_input.toLowerCase()))
        );
    };

    /**
     * @param {string} tag_name
     */
    selectTag = (tag_name) => {
        // we make it so only one tag can be selected at a time
        if (this.private_state.selected_tags.has(tag_name)) {
            this.private_state.selected_tags.delete(tag_name);
            return;
        }
        // delete this line if you want to be able to select multiple tags ( you will have to change the template too )
        this.private_state.selected_tags.clear();
        this.private_state.selected_tags.add(tag_name);
    };
    focusSearch = () => {
        this.private_state.search_is_focused = true;
        // we make it so tags are automatically deselected
        // when the search input is focused
        // ( i made it this way because when the search bar opens
        // the tags are not visible anymore ( on the small size of the screen ))
        // also, the tags provide a more vague way to filter the products
        // ( maybe you don't know exactly what you want ), while the search bar
        // is more precise; ex: you want a Coca Cola, not a soda in general
        this.private_state.selected_tags.clear();
    };
    closeSearch = () => {
        this.private_state.search_is_focused = false;
        this.private_state.search_input = "";
    };
    /**
     * @param {Set} set1
     * @param {Set} set2
     * @returns
     * @description returns true if set1 is a subset of set2
     *
     * example:
     * set1 = {1, 2, 3}
     * set2 = {1, 2, 3, 4}
     * setIsSubset(set1, set2) returns true
     *
     * set1 = {1, 2, 3}
     * set2 = {1, 2, 4}
     * setIsSubset(set1, set2) returns false
     *
     */
    setIsSubset(set1, set2) {
        for (const item of set1) {
            if (!set2.has(item)) {
                return false;
            }
        }
        return true;
    }
    /**
     * @param { Set } set1
     * @param { Set } set2
     * @returns { boolean }
     * @description returns true if the two sets are equal;
     * the order of the elements in the sets does not matter
     */
    areSetsEqual(set1, set2) {
        return set1.size === set2.size && this.setIsSubset(set1, set2);
    }
    static components = { NavBar };
}
ProductList.template = "ProductList";
export default { ProductList };
