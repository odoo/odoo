import { Component, useRef, onMounted, onWillUnmount, useEffect, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";

import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { CategoryListPopup } from "@pos_self_order/app/components/category_list_popup/category_list_popup";
import { useCategoryScrollSpy } from "../../utils/category_scrollspy_hook";
import { useDraggableScroll } from "../../utils/scroll_dnd_hook";
import { scrollItemIntoViewX } from "../../utils/scroll";
import { useScrollShadow, useHorizontalScrollShadow } from "../../utils/scroll_shadow_hook";

let savedScrollTop = 0;

export class ProductListPage extends Component {
    static template = "pos_self_order.ProductListPage";
    static components = { OrderWidget, ProductCard };
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");
        this.categoryListRef = useRef("category_list");
        this.subCategoryListRef = useRef("sub_category_list");
        this.productListRef = useRef("product_list");
        this.subCategoryContainerRef = useRef("sub_cat_container");

        const initCategories = !this.selfOrder.currentCategory;
        if (initCategories) {
            this.selfOrder.computeAvailableCategories();
        }
        const availableCategories = this.selfOrder.availableCategories;
        const topCategories = availableCategories.filter((category) => !category.parent_id);
        const selectedCategory =
            initCategories && topCategories.length > 0
                ? topCategories[0]
                : this.selfOrder.currentCategory;

        this.state = useState({
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
        useHorizontalScrollShadow(this.categoryListRef, useRef("category_container"));
        useDraggableScroll(this.subCategoryListRef);

        useEffect(
            (lines) => {
                this.state.quantityByProductTmplId = lines
                    .filter((line) => !line.combo_parent_id)
                    .reduce((acc, { product_id, changes: { qty } }) => {
                        const tmplId = product_id.product_tmpl_id.id;
                        if (tmplId != null) {
                            acc[tmplId] = (acc[tmplId] || 0) + qty;
                        }
                        return acc;
                    }, {});
            },
            () => [this.selfOrder.currentOrder.lines]
        );

        onMounted(() => {
            this.toggleSubCategoryPanel();
            this.ensureCategoryVisible();
            if (this.productListRef.el) {
                this.productListRef.el.scrollTop = savedScrollTop;
            }
        });

        onWillUnmount(() => {
            this.selfOrder.currentCategory = this.state.selectedCategory;
            savedScrollTop = this.productListRef.el?.scrollTop || 0;
        });
    }

    selectCategory(category) {
        this.state.selectedCategory = category;
        if (this.selfOrder.kioskMode) {
            if (!category.parent_id) {
                this.toggleSubCategoryPanel();
            }
            this.ensureCategoryVisible();
            this.productListRef.el?.scrollTo({ top: 0 });
        } else {
            this.scrollToCategory(category.id);
        }
    }

    ensureCategoryVisible() {
        if (!this.selfOrder.kioskMode) {
            return;
        }

        scrollItemIntoViewX(
            this.categoryListRef.el,
            `[data-category-pill="${this.selectedCategory.id}"]`,
            { edgePadding: 20, minRightGap: this.categoryListRef.el.offsetWidth / 3 }
        );
    }

    get topSelectedCategory() {
        return this.selectedCategory?.parent_id || this.selectedCategory;
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
        if (currentCategory.parent_id) {
            return currentCategory.parent_id.child_ids;
        }
        return currentCategory.child_ids || [];
    }

    get productCategories() {
        if (this.selfOrder.kioskMode) {
            return [this.selectedCategory];
        }
        return this.state.topCategories;
    }

    getProducts(category) {
        const products =
            category.associatedProducts || this.selfOrder.productByCategIds[category.id] || [];

        if (!products.length) {
            return [];
        }

        return products.filter(
            (product) => product.self_order_available && this.selfOrder.isProductAvailable(product)
        );
    }

    toggleSubCategoryPanel() {
        if (!this.selfOrder.kioskMode) {
            return;
        }

        const el = this.subCategoryContainerRef.el;
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

    selectProduct(product, target) {
        this.selfOrder.selectProduct(product, { target });
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
