import {
    Component,
    onWillStart,
    useRef,
    onMounted,
    onWillUnmount,
    useEffect,
    useState,
} from "@odoo/owl";
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
        this.state = useState({
            quantityByProductTmplId: {},
        });

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

        onWillStart(() => {
            if (!this.selfOrder.currentCategory) {
                this.selfOrder.computeAvailableCategories();
            }
        });

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

            this.initCategoriesDragToScroll();
        });

        onWillUnmount(() => {
            if (this.catOnMouseMove) {
                window.removeEventListener("mousemove", this.catOnMouseMove);
                window.removeEventListener("mouseup", this.catOnMouseUp);
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
    }

    isProductAvailable(product) {
        if (product.pos_categ_ids.length === 0) {
            return true;
        }
        return product.pos_categ_ids.some((categ) => this.selfOrder.isCategoryAvailable(categ.id));
    }

    get selectedCategory() {
        return this.selfOrder.currentCategory;
    }

    review() {
        this.router.navigate("cart");
    }

    get products() {
        return this.selfOrder.productByCategIds[this.selectedCategory.id] || [];
    }

    get categories() {
        return this.selfOrder.availableCategories;
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
     *  for non-touch environments only.
     */
    initCategoriesDragToScroll() {
        if (hasTouch()) {
            return;
        }

        let isDragging = false;
        let startX;
        let scrollLeft;

        const container = this.categoryListRef.el;
        container.addEventListener("mousedown", (e) => {
            isDragging = true;

            startX = e.pageX - container.offsetLeft;
            scrollLeft = container.scrollLeft;
        });
        this.catOnMouseUp = (e) => {
            if (!isDragging) {
                return;
            }
            e.preventDefault();
            isDragging = false;
        };
        this.catOnMouseMove = (e) => {
            if (!isDragging) {
                return;
            }

            e.preventDefault();
            const x = e.pageX - container.offsetLeft;
            const walk = x - startX;
            container.scrollLeft = scrollLeft - walk;
        };
        window.addEventListener("mouseup", this.catOnMouseUp);
        window.addEventListener("mousemove", this.catOnMouseMove);
    }
}
