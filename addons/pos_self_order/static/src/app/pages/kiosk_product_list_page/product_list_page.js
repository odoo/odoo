import { Component, useRef, onMounted, onWillUnmount, useEffect, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { hasTouch } from "@web/core/browser/feature_detection";

import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { _t } from "@web/core/l10n/translation";

export class KioskProductListPage extends Component {
    static template = "pos_self_order.KioskProductListPage";
    static components = { OrderWidget };
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");
        this.categoryListRef = useRef("category_list");
        this.subCategoryListRef = useRef("sub_category_list");
        this.subCategoryContainerRef = useRef("sub_cat_container");
        this.state = useState({
            quantityByProductTmplId: {},
            topCategories: [],
            subCategories: [],
        });

        const initCategories = !this.selfOrder.currentCategory;
        if (initCategories) {
            this.selfOrder.computeAvailableCategories();
        }
        this.state.topCategories = this.selfOrder.availableCategories.filter((c) => !c.parent_id);
        if (initCategories) {
            this.selfOrder.currentCategory = this.state.topCategories[0];
        }
        this.state.subCategories = this.getSubCategories();

        useEffect(
            (lines) => {
                this.state.quantityByProductTmplId = lines
                    .filter((line) => !line.combo_parent_id)
                    .reduce((acc, { product_id, qty }) => {
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
            // Ensure the selected category is visible
            const container = this.categoryListRef.el;
            const selected = container.querySelector(".selected");

            if (container && selected) {
                const containerLeft = container.scrollLeft;
                const containerRight = containerLeft + container.clientWidth;

                const selectedLeft = selected.offsetLeft + 50;
                const selectedRight = selectedLeft + selected.offsetWidth + 50;

                if (selectedLeft < containerLeft) {
                    container.scrollLeft = selectedLeft;
                } else if (selectedRight > containerRight) {
                    container.scrollLeft = selectedRight - container.clientWidth;
                }
            }

            this.initCategoriesDragToScroll(this.categoryListRef.el, this.categoryListRef);
            this.initCategoriesDragToScroll(
                this.subCategoryContainerRef.el,
                this.subCategoryListRef
            );
        });

        onWillUnmount(() => {
            if (this.scrollMouseListeners) {
                for (const { onMouseMove, onMouseUp } of this.scrollMouseListeners) {
                    window.removeEventListener("mousemove", onMouseMove);
                    window.removeEventListener("mouseup", onMouseUp);
                }
            }
        });
    }

    back() {
        this.dialog.add(CancelPopup, {
            title: _t("Cancel order"),
            confirm: () => {
                this.router.navigate("categories");
            },
        });
    }

    selectCategory(category) {
        this.selfOrder.currentCategory = category;
        if (!category.parent_id) {
            this.toggleSubCategoryPanel();
        }
    }

    isProductAvailable(product) {
        if (product.pos_categ_ids.length === 0) {
            return true;
        }
        return product.pos_categ_ids.some((categ) => this.selfOrder.isCategoryAvailable(categ.id));
    }

    get topSelectedCategory() {
        return this.selectedCategory?.parent_id || this.selectedCategory;
    }

    get selectedCategory() {
        return this.selfOrder.currentCategory;
    }

    getSubCategories() {
        const currentCategory = this.selfOrder.currentCategory;
        if (!currentCategory) {
            return [];
        }
        if (currentCategory.parent_id) {
            return currentCategory.parent_id.child_ids;
        }
        return currentCategory.child_ids || [];
    }

    toggleSubCategoryPanel() {
        const el = this.subCategoryContainerRef.el;
        const nextSubCategories = this.getSubCategories();
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

    get products() {
        return this.selfOrder.productByCategIds[this.selectedCategory.id] || [];
    }

    selectProduct(product, target) {
        if (!product.self_order_available || !this.isProductAvailable(product)) {
            return;
        }
        if (product.isCombo()) {
            this.router.navigate("combo_selection", { id: product.id });
        } else if (product.isConfigurable() || product.public_description) {
            this.router.navigate("product", { id: product.id });
        } else {
            if (!this.selfOrder.ordering) {
                return;
            }
            this.flyToCart(target);
            this.selfOrder.addToCart(product, 1);
        }
    }

    flyToCart(target) {
        const productEl = target.closest(".o_kiosk_product_box");

        const toOrder = document.querySelector(".to-order");
        if (!toOrder || window.getComputedStyle(toOrder).display === "none" || !productEl) {
            return;
        }

        const picRect = productEl.getBoundingClientRect();
        const clonedPic = productEl.cloneNode(true);
        const toOrderRect = toOrder.getBoundingClientRect();

        clonedPic.classList.add("position-fixed", "z-1");
        clonedPic.style.top = `${picRect.top}px`;
        clonedPic.style.left = `${picRect.left}px`;
        clonedPic.style.width = `${picRect.width}px`;
        clonedPic.style.height = `${picRect.height}px`;
        clonedPic.style.transition = "all 400ms cubic-bezier(0.6, 0, 0.9, 1.000)";

        document.body.appendChild(clonedPic);

        requestAnimationFrame(() => {
            const offsetTop = toOrderRect.top - picRect.top - picRect.height * 0.5;
            const offsetLeft = toOrderRect.left - picRect.left - picRect.width * 0.25;
            clonedPic.style.transform =
                "translateY(" + offsetTop + "px) translateX(" + offsetLeft + "px) scale(0.5)";
            clonedPic.style.opacity = "0"; // Fading out the card
        });

        clonedPic.addEventListener("transitionend", () => {
            clonedPic.remove();
        });
    }

    /**
     *  The category panel scrollbars are hidden, so we allow scrolling via drag-and-drop
     */
    initCategoriesDragToScroll(container, scrollContainer) {
        if (hasTouch()) {
            return;
        }

        let isDragging = false;
        let startX;
        let scrollLeft;

        const onMouseDown = (e) => {
            if (!scrollContainer.el) {
                return;
            }
            isDragging = true;
            startX = e.pageX - scrollContainer.el.offsetLeft;
            scrollLeft = scrollContainer.el.scrollLeft;
        };

        const onMouseMove = (e) => {
            if (!isDragging || !scrollContainer.el) {
                return;
            }

            e.preventDefault();
            const x = e.pageX - scrollContainer.el.offsetLeft;
            const walk = x - startX;
            scrollContainer.el.scrollLeft = scrollLeft - walk;
        };

        const onMouseUp = (e) => {
            if (!isDragging) {
                return;
            }
            e.preventDefault();
            isDragging = false;
        };

        container.addEventListener("mousedown", onMouseDown);
        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);

        this.scrollMouseListeners = this.scrollMouseListeners || [];
        this.scrollMouseListeners.push({ onMouseMove, onMouseUp });
    }
}
