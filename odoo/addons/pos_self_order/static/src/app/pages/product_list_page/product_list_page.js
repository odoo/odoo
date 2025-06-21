/** @odoo-module */

import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";
import { useService, useChildRef } from "@web/core/utils/hooks";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { _t } from "@web/core/l10n/translation";
import { fuzzyLookup } from "@web/core/utils/search";

export class ProductListPage extends Component {
    static template = "pos_self_order.ProductListPage";
    static components = { ProductCard, OrderWidget };

    setup() {
        this.selfOrder = useSelfOrder();
        this.dialog = useService("dialog");
        this.router = useService("router");
        this.productsList = useRef("productsList");
        this.categoryList = useRef("categoryList");
        this.searchInput = useRef("searchInput");
        this.currentProductCard = useChildRef();
        this.state = useState({
            search: false,
            searchInput: "",
        });
        this.categoryButton = Object.fromEntries(
            Array.from(this.selfOrder.categoryList).map((category) => {
                return [category.id, useRef(`category_${category.id}`)];
            })
        );

        useEffect(
            () => {
                if (this.state.search) {
                    this.searchInput.el.focus();
                }
            },
            () => [this.state.search]
        );

        useEffect(
            () => {
                if (this.selfOrder.lastEditedProductId) {
                    this.scrollTo(this.currentProductCard, { behavior: "instant" });
                }
                const scrollSpyContentEl = document.getElementById("scrollspy-products");
                const scrollSpy = ScrollSpy.getOrCreateInstance(scrollSpyContentEl);
                const currentCategId = this.selfOrder.currentCategory.id;
                const categ = document.querySelectorAll(`[categId="${currentCategId}"]`);
                if (categ[0]) {
                    categ[0].scrollIntoView();
                }
                const onActivateScrollSpy = () => {
                    const categId = parseInt(scrollSpy._activeTarget.split("_")[1]);
                    this.selfOrder.currentCategory = this.selfOrder.pos_category.find(
                        (categ) => categ.id === categId
                    );
                };
                scrollSpyContentEl.addEventListener("activate.bs.scrollspy", onActivateScrollSpy);
                return () => {
                    scrollSpyContentEl.removeEventListener(
                        "activate.bs.scrollspy",
                        onActivateScrollSpy
                    );
                };
            },
            () => []
        );

        useEffect(
            () => {
                const category = this.selfOrder.currentCategory;
                const categBtn = this.categoryButton[category.name]?.el;

                if (!categBtn) {
                    return;
                }

                this.categoryList.el.scroll({
                    left: categBtn.offsetLeft + categBtn.offsetWidth / 2 - window.innerWidth / 2,
                    behavior: "smooth",
                });
            },
            () => [this.selfOrder.currentCategory]
        );
    }

    focusSearch() {
        this.state.search = !this.state.search;

        if (!this.state.search) {
            this.state.searchInput = "";
        }
    }

    getFilteredProducts(products) {
        return fuzzyLookup(
            this.state.searchInput,
            products,
            (product) => product.name + product.description_sale
        );
    }

    scrollTo(ref = null, { behavior = "smooth" } = {}) {
        this.productsList.el.scroll({
            top: ref?.el ? ref.el.offsetTop - this.productsList.el.offsetTop : 0,
            behavior,
        });
    }

    review() {
        this.router.navigate("cart");
    }

    back() {
        if (this.selfOrder.config.self_ordering_mode !== "kiosk") {
            this.router.navigate("default");
            return;
        }

        this.dialog.add(CancelPopup, {
            title: _t("Cancel order"),
            confirm: () => {
                this.router.navigate("default");
            },
        });
    }
}
