/** @odoo-module */

import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { useAutofocus, useChildRef } from "@web/core/utils/hooks";
import { NavBar } from "@pos_self_order/Components/NavBar/NavBar";
import { FloatingButton } from "@pos_self_order/Components/FloatingButton/FloatingButton";
import { ProductCard } from "@pos_self_order/Components/ProductCard/ProductCard";
import { fuzzyLookup } from "@web/core/utils/search";
export class ProductList extends Component {
    static template = "pos_self_order.ProductList";
    static props = [];
    static components = {
        NavBar,
        FloatingButton,
        ProductCard,
    };
    setup() {
        this.privateState = useState({
            selectedTag: "",
            searchIsFocused: false,
            searchInput: "",
            navbarIsShown: true,
            scrollingDown: false,
            scrolling: false,
        });
        this.selfOrder = useSelfOrder();
        useAutofocus({ refName: "searchInput", mobile: true });
        this.productsList = useRef("productsList");

        // reference to the last visited product
        // (used to scroll back to it when the user comes back from the product page)
        this.currentProductCard = useChildRef();

        // object with references to each tag heading
        this.productGroup = Object.fromEntries(
            Array.from(this.selfOrder.tagList).map((tag) => {
                return [tag, useRef(`productsWithTag_${tag}`)];
            })
        );
        this.tagButtons = Object.fromEntries(
            Array.from(this.selfOrder.tagList).map((tag) => {
                return [tag, useRef(`tag_${tag}`)];
            })
        );
        this.tagList = useRef("tagList");
        this.header = useRef("header");
        this.productPage = useRef("productPage");
        this.main = useRef("main");
        this.orderButton = useRef("orderButton");

        onMounted(() => {
            // TODO: replace this logic with dvh once it is supported
            this.main.el.style.height = `${window.innerHeight}px`;
            // this.main.el.style.height = `100%`;

            this.headerHeight = this.header.el.offsetHeight;
            this.navbarHeight = this.header.el.querySelector("nav").offsetHeight;
            // TODO: add dvh once it is supported
            // this.productsList.el.style.height = `calc(${window.innerHeight}px - ${this.navbarHeight}px)`;
            this.productsList.el.style.height = `${
                window.innerHeight - this.headerHeight - this.orderButton?.el?.offsetHeight
            }px`;
            // this.productsList.el.style.height = `100%`;
            // this.productsList.el.style.paddingBottom = `100px`;
            this.productsList.el.style.paddingBottom = `0px`;
            console.log("productsList", this.productsList.el.innerHeight);

            // if the user is coming from the product page
            // we scroll back to the product card that he was looking at before
            if (this.selfOrder.currentProduct) {
                this.scrollTo(this.currentProductCard);
            }
        });
        // this useEffect is used to hide the navbar when the user is scrolling down
        // ( so the list looks like it's pushing the navbar up )
        useEffect(
            (scrollingDown, searchIsFocused) => {
                if (searchIsFocused) {
                    return;
                }
                const threshold = 60;
                let lastScrollY = this.productsList.el?.scrollTop;
                let ticking = false;

                const updateScrollDir = () => {
                    if (!this.productsList.el) {
                        return;
                    }
                    const scrollY = this.productsList.el?.scrollTop;
                    const amountScrolled = Math.abs(scrollY - lastScrollY);
                    if (amountScrolled < threshold) {
                        ticking = false;
                        return;
                    }
                    scrollingDown = scrollY > lastScrollY;
                    if (scrollingDown === this.privateState.navbarIsShown) {
                        this.toggleNavbar(this.privateState.navbarIsShown);
                    }
                    lastScrollY = scrollY > 0 ? scrollY : 0;
                    ticking = false;
                };

                const onScroll = () => {
                    if (!ticking) {
                        // this makes the scrolling smooth
                        window.requestAnimationFrame(updateScrollDir);
                        ticking = true;
                    }
                };
                this.productsList.el.addEventListener("scroll", onScroll);
                return () => this.productsList.el.removeEventListener("scroll", onScroll);
            },
            () => [this.privateState.scrollingDown, this.privateState.searchIsFocused]
        );
        // this IntersectionObserver is used to highlight the tag (in the header)
        // of the category that is currently visible in the viewport
        useEffect(
            (searchIsFocused) => {
                if (searchIsFocused) {
                    return;
                }
                const OBSERVING_WINDOW_HEIGHT = 5;
                const observer = new IntersectionObserver(
                    (entries) => {
                        const entry = entries.filter((entry) => entry.isIntersecting)?.[0];
                        if (entry) {
                            this.privateState.selectedTag =
                                entry.target.querySelector("h3").textContent;
                            // we scroll the tag list horizontally so that the selected tag is in the middle of the screen
                            this.tagList?.el?.scroll({
                                top: 0,
                                left:
                                    this.tagButtons[this.privateState.selectedTag].el.offsetLeft -
                                    window.innerWidth / 2,
                                behavior: "smooth",
                            });
                        }
                    },
                    {
                        root: this.productsList.el,
                        rootMargin: `0px 0px -${
                            this.productsList.el.offsetHeight -
                            parseInt(this.productsList.el.style.paddingBottom) -
                            OBSERVING_WINDOW_HEIGHT
                        }px 0px`,
                        // rootMargin: `0px 0px -${
                        //     this.productsList.el.height -
                        //     parseInt(this.productsList.el.style.paddingBottom) -
                        //     OBSERVING_WINDOW_HEIGHT
                        // }px 0px`,
                    }
                );
                Object.keys(this.productGroup).forEach((tag) => {
                    observer.observe(this.productGroup[tag]?.el);
                });
                return () => {
                    observer.disconnect();
                };
            },
            () => [this.privateState.searchIsFocused]
        );
    }
    /**
     * This function hides or shows the navbar by sliding the whole productPage up or down
     * @param {boolean} hide - true if the navbar should be hidden, false otherwise
     */
    toggleNavbar(hide) {
        const animationSteps = hide
            ? [{ top: "0px" }, { top: `-${this.navbarHeight}px` }]
            : [{ top: `-${this.navbarHeight}px` }, { top: "0px" }];
        this.productPage.el.animate(animationSteps, {
            duration: 200,
            fill: "forwards",
        });
        this.privateState.navbarIsShown = !this.privateState.navbarIsShown;
        this.productsList.el.style.height = `${
            window.innerHeight -
            this.headerHeight -
            // this.orderButton.el.offsetHeight +
            this.navbarHeight * !this.privateState.navbarIsShown
        }px`;
    }

    scrollToTop() {
        this.productsList?.el?.scroll({
            top: 0,
            left: 0,
            behavior: "smooth",
        });
    }
    /**
     * This function scrolls the productsList to the ref passed as argument,
     *            it takes into account the height of the header
     * @param {Object} ref - the ref to scroll to
     */
    scrollTo(ref) {
        const y = ref?.el.offsetTop;
        // the intersection observer will detect on which product category we are and
        // it is possible that after scrolling we are a couple of pixels short of the desired category
        // so it actually sees the previous category. To avoid this we add a small correction
        const SCROLL_CORRECTION = 4;
        const scrollOffset = this.headerHeight - SCROLL_CORRECTION;
        this.productsList?.el?.scroll({
            top: y - scrollOffset,
            behavior: "smooth",
        });
    }
    /**
     * This function returns the list of products that should be displayed;
     *             it filters the products based on the search input
     * @returns {Object} the list of products that should be displayed
     */
    filteredProducts() {
        if (!this.privateState.searchInput) {
            return this.selfOrder.products;
        }
        return fuzzyLookup(
            this.privateState.searchInput,
            this.selfOrder.products,
            (product) => product.name + product.description_sale
        );
    }
    /**
     * This function is called when a tag is clicked; it selects the chosen tag and deselects all the other tags
     * @param {string} tag_name
     */
    selectTag(tag_name) {
        if (this.privateState.selectedTag === tag_name) {
            this.privateState.selectedTag = "";
            this.scrollToTop();
            return;
        }
        // When the user clicks on a tag, we scroll to the part of the page
        // where the products with that tag are displayed.
        // after the scrolling is done, the intersection observer will
        // automatically set the privateState.selectedTag to the tag_name
        this.scrollTo(this.productGroup[tag_name]);
    }
    /**
     * This function is called when the search button is clicked.
     * It sets the state so the search input is focused.
     * It also deselects all the selected tags
     */
    focusSearch() {
        this.privateState.searchIsFocused = true;
        if (this.privateState.navbarIsShown) {
            this.toggleNavbar(true);
        }
        this.scrollToTop();
    }
    /**
     * This function is called when the search input 'x' button is clicked
     */
    closeSearch() {
        this.privateState.searchIsFocused = false;
        this.privateState.searchInput = "";
    }
}
