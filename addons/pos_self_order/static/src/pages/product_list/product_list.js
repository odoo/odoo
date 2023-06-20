/** @odoo-module */

import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/self_order_service";
import { useAutofocus, useChildRef, useService } from "@web/core/utils/hooks";
import { NavBar } from "@pos_self_order/components/navbar/navbar";
import { ProductCard } from "@pos_self_order/components/product_card/product_card";
import { fuzzyLookup } from "@web/core/utils/search";
import { useScrollDirection } from "@pos_self_order/hooks/use_scroll_direction";
import { useDetection } from "@pos_self_order/hooks/use_detection";
import { Transition } from "@web/core/transition";

export class ProductList extends Component {
    static template = "pos_self_order.ProductList";
    static props = [];
    static components = {
        NavBar,
        ProductCard,
        Transition,
    };
    setup() {
        // reference to the last visited product
        // (used to scroll back to it when the user comes back from the product page)
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.productsList = useRef("productsList");
        this.categoryList = useRef("categoryList");
        this.currentProductCard = useChildRef();
        this.search = useState({
            isFocused: false,
            input: "",
        });

        useAutofocus({ refName: "searchInput", mobile: true });

        this.productGroups = Object.fromEntries(
            Array.from(this.selfOrder.categoryList).map((category) => {
                return [category, useRef(`productsWithCategory_${category}`)];
            })
        );

        this.categoryButton = Object.fromEntries(
            Array.from(this.selfOrder.categoryList).map((category) => {
                return [category, useRef(`category_${category}`)];
            })
        );

        onMounted(() => {
            if (this.selfOrder.lastEditedProductId) {
                this.scrollTo(this.currentProductCard, { behavior: "instant" });
            }
        });

        // this is used to hide the navbar when the user is scrolling down
        this.scroll = useScrollDirection(this.productsList);

        // This detects the product group where we are currently scrolled
        this.currentProductGroup = useDetection(this.productsList, this.productGroups, () => [
            this.search.isFocused,
        ]);

        useEffect(
            () => {
                const category = this.categoryButton[this.currentProductGroup.name]?.el;

                if (!category) {
                    return;
                }

                this.categoryList.el.scroll({
                    left: category.offsetLeft + category.offsetWidth / 2 - window.innerWidth / 2,
                    behavior: "smooth",
                });
            },
            () => [this.currentProductGroup.name]
        );
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
        // we also scroll the categoryList in the header)
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
     * This function is called when a category is clicked;
     * @param {string} category_name
     */
    categoryOnClick(category_name) {
        // When the user clicks on a category, we scroll to the part of the page
        // where the products with that category are displayed.
        // We don't have to manually mark the category as selected because the
        // useDetection hook will do it for us.
        this.scrollTo(
            this.currentProductGroup.name != category_name
                ? this.productGroups[category_name]
                : null
        );
    }

    focusSearch() {
        this.search.isFocused = true;
        this.scrollTo();
    }

    closeSearch() {
        this.search.isFocused = false;
        this.search.input = "";
    }
}
