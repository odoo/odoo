/** @odoo-module */

import { Component, useEffect, useRef } from "@odoo/owl";
import { useSelfOrderKiosk } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { ProductCard } from "@pos_self_order/kiosk/components/product_card/product_card";
import { useDetection } from "@pos_self_order/common/hooks/use_detection";

export class ProductList extends Component {
    static template = "pos_self_order.ProductList";
    static components = { ProductCard };

    setup() {
        this.selfOrderKiosk = useSelfOrderKiosk();
        this.productsList = useRef("productsList");
        this.categoryList = useRef("categoryList");

        this.productGroups = Object.fromEntries(
            Array.from(this.selfOrderKiosk.categoryList).map((category) => {
                return [category, useRef(`productsWithCategory_${category}`)];
            })
        );

        this.categoryButton = Object.fromEntries(
            Array.from(this.selfOrderKiosk.categoryList).map((category) => {
                return [category, useRef(`category_${category}`)];
            })
        );

        this.currentProductGroup = useDetection(this.productsList, this.productGroups, () => []);

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

    categoryClicked(category) {
        this.scrollTo(
            this.currentProductGroup.name != category ? this.productGroups[category] : null
        );
    }

    scrollTo(ref = null, { behavior = "smooth" } = {}) {
        this.productsList.el.scroll({
            top: ref?.el ? ref.el.offsetTop - this.productsList.el.offsetTop : 0,
            behavior,
        });
    }
}
