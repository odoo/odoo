import { Component, useEffect, useRef, onWillStart } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";
import { useService, useChildRef } from "@web/core/utils/hooks";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { _t } from "@web/core/l10n/translation";

export class ProductListPage extends Component {
    static template = "pos_self_order.ProductListPage";
    static components = { ProductCard, OrderWidget };
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.dialog = useService("dialog");
        this.router = useService("router");
        this.productsList = useRef("productsList");
        this.categoryList = useRef("categoryList");
        this.currentProductCard = useChildRef();
        this.categoryButton = Object.fromEntries(
            this.selfOrder.productCategories.map((category) => {
                return [category.id, useRef(`category_${category.id}`)];
            })
        );

        useEffect(
            () => {
                if (!this.productsList.el) {
                    return;
                }
                if (this.selfOrder.lastEditedProductId) {
                    this.scrollTo(this.currentProductCard, { behavior: "instant" });
                }
                const scrollSpyContentEl = this.productsList.el;
                const currentCategId = this.selfOrder.currentCategory?.id;
                const categ = document.querySelectorAll(`[categId="${currentCategId}"]`);
                if (categ[0]) {
                    categ[0].scrollIntoView();
                }
                const onActivateScrollSpy = ({ relatedTarget }) => {
                    const categId = parseInt(relatedTarget.getAttribute("href").split("_")[1]);
                    this.selfOrder.currentCategory = this.selfOrder.models["pos.category"].find(
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
                const categBtn = this.categoryButton[category?.name]?.el;

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

        onWillStart(() => {
            this.selfOrder.computeAvailableCategories();
        });
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
