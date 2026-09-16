import { Component, onMounted, onWillUnmount, computed, proxy, signal } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { CategoryListPopup } from "@pos_self_order/app/components/category_list_popup/category_list_popup";
import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";
import { useCategoryScrollSpy } from "../../utils/category_scrollspy_hook";
import { useDraggableScroll } from "../../utils/scroll_dnd_hook";
import { scrollItemIntoViewX } from "../../utils/scroll";
import { useScrollShadow, useHorizontalScrollShadow } from "../../utils/scroll_shadow_hook";

let savedScrollTop = 0;

export class ProductListPage extends Component {
    static template = "pos_self_order.ProductListPage";
    static components = { OrderWidget, ProductCard };

    categoryListRef = signal.ref();
    subCategoryListRef = signal.ref();
    productListRef = signal.ref();
    subCategoryContainerRef = signal.ref();
    categoryContainerRef = signal.ref();

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");
        this.ui = useService("ui");

        const initCategories = !this.selfOrder.currentCategory;
        if (initCategories) {
            this.selfOrder.computeAvailableCategories();
        }
        const topCategories = this.selfOrder.topCategories;
        const selectedCategory =
            initCategories && topCategories.length > 0
                ? topCategories[0]
                : this.selfOrder.currentCategory;

        this.state = proxy({
            selectedCategory: selectedCategory,
            quantityByProductTmplId: {},
            topCategories: topCategories,
            subCategories: [],
        });

        if (!this.selfOrder.kioskMode) {
            this.scrollToCategory = useCategoryScrollSpy(
                this.state.selectedCategory?.id,
                this.categoryListRef,
                this.productListRef,
                (catId) => {
                    this.state.selectedCategory = this.state.topCategories.find(
                        (c) => c.id === catId
                    );
                }
            ).scrollToCategory;
        }

        this.scrollShadow = useScrollShadow(this.productListRef);
        useDraggableScroll(this.categoryListRef);
        useHorizontalScrollShadow(this.categoryListRef, this.categoryContainerRef);
        useDraggableScroll(this.subCategoryListRef);
        Object.defineProperty(this.state, "quantityByProductTmplId", {
            get: computed(() =>
                this.selfOrder.currentOrder.lines
                    .filter((line) => !line.combo_parent_id)
                    .reduce((acc, { product_id, changes: { qty } }) => {
                        const tmplId = product_id.product_tmpl_id.id;
                        if (tmplId != null) {
                            acc[tmplId] = (acc[tmplId] || 0) + qty;
                        }
                        return acc;
                    }, {})
            ),
        });

        onMounted(() => {
            this.toggleSubCategoryPanel();
            this.ensureCategoryVisible();
            if (this.productListRef()) {
                this.productListRef().scrollTop = savedScrollTop;
            }
        });

        onWillUnmount(() => {
            this.selfOrder.currentCategory = this.state.selectedCategory;
            savedScrollTop = this.productListRef()?.scrollTop || 0;
        });
    }

    get showBackButton() {
        const order = this.selfOrder.currentOrder;
        return Object.keys(order.changes).length === 0 || order.lines.length === 0;
    }

    get backTargetPage() {
        const order = this.selfOrder.currentOrder;
        const payAfter = this.selfOrder.config.self_ordering_pay_after;
        const alreadyOrdered =
            payAfter === "meal" && Object.keys(order.uiState.lineChanges).length > 0;
        return this.selfOrder.hasPresets() && !alreadyOrdered ? "location" : "default";
    }

    discardOrder() {
        this.dialog.add(CancelPopup, {
            title: _t("Cancel order"),
            confirm: () => {
                this.selfOrder.cancelOrder();
                this.router.navigate("default");
            },
        });
    }

    get checkoutDisabled() {
        const order = this.selfOrder.currentOrder;
        return order.lines.length === 0 || order.unsentLines.length === 0;
    }

    get total() {
        const orderLineNotSend = this.selfOrder.orderLineNotSend;
        return {
            count: orderLineNotSend.count,
            price:
                this.selfOrder.config.iface_tax_included === "total"
                    ? orderLineNotSend.priceWithTax
                    : orderLineNotSend.priceWithoutTax,
        };
    }

    selectCategory(category) {
        this.state.selectedCategory = category;
        if (this.selfOrder.kioskMode) {
            if (!category.parent_id) {
                this.toggleSubCategoryPanel();
            }
            this.ensureCategoryVisible();
            this.productListRef()?.scrollTo({ top: 0 });
        } else {
            this.scrollToCategory(category.id);
        }
    }

    ensureCategoryVisible() {
        if (!this.selfOrder.kioskMode) {
            return;
        }

        scrollItemIntoViewX(
            this.categoryListRef(),
            `[data-category-pill="${this.selectedCategory.id}"]`,
            { edgePadding: 20, minRightGap: this.categoryListRef().offsetWidth / 3 }
        );
    }

    get topSelectedCategory() {
        const category = this.selectedCategory;
        return category?.parent_id?.self_order_available ? category.parent_id : category;
    }

    get selectedCategory() {
        return this.state.selectedCategory;
    }

    getSubCategories() {
        if (!this.selfOrder.kioskMode) {
            return [];
        }

        const currentCategory = this.state.selectedCategory;
        if (!currentCategory) {
            return [];
        }
        const children = currentCategory.parent_id
            ? currentCategory.parent_id.child_ids
            : currentCategory.child_ids;
        return (children || []).filter((category) =>
            this.selfOrder.isCategoryAvailable(category.id)
        );
    }

    get productCategories() {
        if (this.selfOrder.kioskMode) {
            return [this.selectedCategory];
        }
        return this.state.topCategories;
    }

    getProducts(category) {
        return (
            category.associatedProducts ||
            this.selfOrder.productByCategIds[category.id] ||
            []
        ).filter(
            (product) => product.self_order_available && this.selfOrder.isProductAvailable(product)
        );
    }

    toggleSubCategoryPanel() {
        if (!this.selfOrder.kioskMode) {
            return;
        }

        const el = this.subCategoryContainerRef();
        const nextSubCategories = this.getSubCategories();
        // Managing this with state would hide the subcategory items before the container finishes closing,
        // causing an awkward visual transition.
        if (this.state.subCategories.length > 0 && nextSubCategories.length === 0) {
            el.classList.remove("show");
            const oldSelectedCat = this.selectedCategory;
            const self = this;
            el.addEventListener("transitionend", function handler(e) {
                if (oldSelectedCat === self.selectedCategory) {
                    self.state.subCategories = [];
                }
                el.removeEventListener("transitionend", handler);
            });
            return;
        } else if (nextSubCategories.length === 0 && this.state.subCategories.length === 0) {
            return;
        }

        this.state.subCategories = nextSubCategories;
        el.classList.add("show");
    }

    review() {
        this.router.navigate("cart");
    }

    displayCategoryList(categories) {
        this.dialog.add(CategoryListPopup, {
            categories: categories,
            onCategorySelected: (cat) => {
                this.selectCategory(cat);
            },
        });
    }
}
