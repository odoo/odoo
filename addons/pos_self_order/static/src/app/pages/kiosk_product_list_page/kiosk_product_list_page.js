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
        this.productListRef = useRef("product_list");
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
        this.productListRef.el?.scrollTo({ top: 0 });
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
        if (this.selectedCategory.child_ids?.length > 0) {
            return this.selectedCategory.associatedProducts;
        }
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

        const ANIMATION_CONFIG = {
            flyDuration: "900ms",
            cartDuration: "200ms",
            flyEasing: "cubic-bezier(0.34, 1.56, 0.64, 1)",
            initialScale: ".65",
            finalScale: "0.05",
            cartScale: "1.08",
            rotation: "5deg",
        };

        const cardRect = productEl.getBoundingClientRect();
        const toOrderRect = toOrder.getBoundingClientRect();
        const offsetTop = toOrderRect.top - cardRect.top;
        const offsetLeft = toOrderRect.left - cardRect.left;

        const clonedPic = productEl.cloneNode(true);
        const initialStyles = {
            top: `${cardRect.top}px`,
            left: `${cardRect.left}px`,
            width: `${cardRect.width}px`,
            height: `${cardRect.height}px`,
            transform: "scale(1)",
            opacity: "1",
            transition: `all ${ANIMATION_CONFIG.flyDuration} ${ANIMATION_CONFIG.flyEasing}`,
            pointerEvents: "none",
        };

        Object.assign(clonedPic.style, initialStyles);
        clonedPic.classList.add("position-fixed", "shadow-lg", "z-1");

        const infosDiv = clonedPic.querySelector(".product-infos");
        if (infosDiv) {
            Object.assign(infosDiv.style, {
                transform: "scale(0.9)",
                transition: `all ${ANIMATION_CONFIG.flyDuration} ${ANIMATION_CONFIG.flyEasing}`,
            });
        }

        document.body.appendChild(clonedPic);

        requestAnimationFrame(() => {
            clonedPic.style.transform = `scale(${ANIMATION_CONFIG.initialScale})`;
            requestAnimationFrame(() => {
                clonedPic.style.transform = `
                    translateY(${offsetTop}px) 
                    translateX(${offsetLeft}px) 
                    scale(${ANIMATION_CONFIG.finalScale}) 
                    rotate(${ANIMATION_CONFIG.rotation})
                `;
                clonedPic.style.opacity = "0";

                if (infosDiv) {
                    infosDiv.style.transform = "scale(0.7)";
                }

                const cartAnimation = {
                    transform: `scale(${ANIMATION_CONFIG.cartScale})`,
                    transition: `transform ${ANIMATION_CONFIG.cartDuration} ${ANIMATION_CONFIG.flyEasing}`,
                };
                Object.assign(toOrder.style, cartAnimation);

                setTimeout(() => {
                    Object.assign(toOrder.style, {
                        transform: "scale(1)",
                        transition: `transform ${ANIMATION_CONFIG.cartDuration} ${ANIMATION_CONFIG.flyEasing}`,
                    });
                }, parseInt(ANIMATION_CONFIG.cartDuration));
            });
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
