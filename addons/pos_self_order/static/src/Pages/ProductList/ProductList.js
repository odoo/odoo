/** @odoo-module */

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { useAutofocus, useChildRef } from "@web/core/utils/hooks";
import { NavBar } from "@pos_self_order/Components/NavBar/NavBar";
import { ProductCard } from "@pos_self_order/Components/ProductCard/ProductCard";
import { fuzzyLookup } from "@web/core/utils/search";
import { useScrollDirection } from "@pos_self_order/Hooks/useScrollDirection";
import { useDetection } from "@pos_self_order/Hooks/useDetection";
import { Transition } from "@web/core/transition";
import { TagSelector } from "@pos_self_order/Components/TagSelector/TagSelector";
import { MainButton } from "@pos_self_order/Components/MainButton/MainButton";

export class ProductList extends Component {
    static template = "pos_self_order.ProductList";
    static props = [];
    static components = {
        NavBar,
        ProductCard,
        Transition,
        TagSelector,
        MainButton,
    };
    setup() {
        this.search = useState({
            isFocused: false,
            input: "",
        });
        this.selfOrder = useSelfOrder();
        useAutofocus({ refName: "input", mobile: true });
        this.productsList = useRef("productsList");

        // reference to the last visited product
        // (used to scroll back to it when the user comes back from the product page)
        this.currentProductCard = useChildRef();

        // object with references to each product group
        this.productGroups = Object.fromEntries(
            Array.from(this.selfOrder.tagList).map((tag) => {
                return [tag, useRef(`productsWithTag_${tag}`)];
            })
        );

        onMounted(() => {
            // if the user is coming from the product page
            // we scroll back to the product card that he was looking at before
            if (this.selfOrder.currentProduct) {
                this.scrollTo(this.currentProductCard, { behavior: "instant" });
            }
        });
        // this is used to hide the navbar when the user is scrolling down
        this.scroll = useScrollDirection(this.productsList);

        // This detects the product group where we are currently scrolled
        this.currentProductGroup = useDetection(this.productsList, this.productGroups, () => [
            this.search.isFocused,
        ]);
    }

    shouldNavbarBeShown() {
        return !this.search.isFocused && !this.scroll.down;
    }

    /**
     * This function scrolls the productsList to the ref passed as argument,
     * or to the top of the page if no ref is passed
     * @param {Object} ref - the ref to scroll to
     */
    scrollTo(ref = null, { behavior = "smooth" } = {}) {
        // it would be convenient to use .scrollIntoView() but it doesn't work if we
        // scroll on multiple elements at the same time. ( when we scroll the productsList
        // we also scroll the tagList in the header)
        this.productsList.el.scroll({
            top: ref?.el ? ref.el.offsetTop - this.productsList.el.offsetTop : 0,
            behavior,
        });
    }
    /**
     * This function returns the list of products that should be displayed;
     *             it filters the products based on the search input
     * @returns {Object} the list of products that should be displayed
     */
    filteredProducts() {
        if (!this.search.input) {
            return this.selfOrder.products;
        }
        return fuzzyLookup(
            this.search.input,
            this.selfOrder.products,
            (product) => product.name + product.description_sale
        );
    }
    /**
     * This function is called when a tag is clicked;
     * @param {string} tag_name
     */
    tagOnClick(tag_name) {
        // When the user clicks on a tag, we scroll to the part of the page
        // where the products with that tag are displayed.
        // We don't have to manually mark the tag as selected because the
        // useDetection hook will do it for us.
        this.scrollTo(
            this.currentProductGroup.name != tag_name ? this.productGroups[tag_name] : null
        );
    }
    /**
     * This function is called when the search button is clicked.
     */
    focusSearch() {
        this.search.isFocused = true;
        this.scrollTo();
    }
    /**
     * This function is called when the 'Close Search'  button is clicked ( the 'x' button )
     */
    closeSearch() {
        this.search.isFocused = false;
        this.search.input = "";
    }
}
