/** @odoo-module */

const { Component, useState } = owl;
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { useAutofocus } from "@web/core/utils/hooks";
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
        useAutofocus({ refName: "searchInput", mobile: true });
    }
    filteredProducts = () => {
        // here we only want to return the products
        // that have the selected tags
        console.log("this.inputRef :>> ", this.inputRef);
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
     * @returns
     */
    itemHasAllOfTheTags = (item, selected_tags) => {
        if (!selected_tags.size) {
            return true;
        }
        for (const tag of selected_tags) {
            if (!item.tag_list.has(tag)) {
                return false;
            }
        }
        return true;
    };
    /**
     * @param {Product} item
     * @param {string} search_input
     * @returns
     * @description returns true if the item matches the search input
     */
    itemMatchesSearch = (item, search_input) => {
        // TODO: maybe there is a smarter function we could use here
        if (!search_input) {
            return true;
        }
        return item.name.toLowerCase().includes(search_input.toLowerCase());
        // TODO: maybe we should also search in the description
        // be careful, the description is not always filled
        // item.description_sale.toLowerCase().includes(search_input.toLowerCase());
    };

    /**
     * @param {string} tag_name
     */
    selectTag = (tag_name) => {
        if (this.private_state.selected_tags.has(tag_name)) {
            this.private_state.selected_tags.delete(tag_name);
            return;
        }
        this.private_state.selected_tags.add(tag_name);
    };
    focusSearch = () => {
        this.private_state.search_is_focused = true;
        // we make it so tags are automatically deselected
        // when the search input is focused
        // TODO: decide if we want this behavior
        // ( i made it this way because when the search bar opens
        // the tags are not visible anymore ( on the small size of the screen ))
        // also, the tags provide a more vague way to filter the products
        // ( maybe you don't know exactly what you want ), while the search bar
        // is more precise; ex: you want a Coca Cola, not a soda in general
        this.private_state.selected_tags.clear();
        // FIXME: this is a hack: we want to focus the input after the search bar
        // is rendered, but we don't know when it is rendered
        // setTimeout(() => {
        //     this.inputRef.el.focus();
        // }, 50);
    };
    closeSearch = () => {
        this.private_state.search_is_focused = false;
        this.private_state.search_input = "";
    };

    static components = { NavBar };
}
ProductList.template = "ProductList";
export default { ProductList };
