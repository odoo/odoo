import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { debounce as debounceFn } from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";

// Widget responsible for openingn the modal (giving out the sale order id)

publicWidget.registry.SaleOrderPortalReorderWidget = publicWidget.Widget.extend({
    selector: ".o_portal_sidebar",
    events: {
        "click .o_wsale_reorder_button": "_onReorder",
    },

    _onReorder(ev) {
        const orderId = parseInt(ev.currentTarget.dataset.saleOrderId);
        const urlSearchParams = new URLSearchParams(window.location.search);
        if (!orderId || !urlSearchParams.has("access_token")) {
            return;
        }
        // Open the modal
        this.call("dialog", "add", ReorderDialog, {
            orderId: orderId,
            accessToken: urlSearchParams.get("access_token"),
        });
    },
});

import { Component, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

// Reorder Dialog

export class ReorderConfirmationDialog extends ConfirmationDialog {
    static template = "website_sale.ReorderConfirmationDialog";
}

export class ReorderDialog extends Component {
    static template = "website_sale.ReorderModal";
    static props = {
        close: Function,
        orderId: Number,
        accessToken: String,
    };
    static components = {
        Dialog,
    };

    setup() {
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.websiteSale = useService("websiteSale");
        this.formatCurrency = formatCurrency;

        onWillStart(this.onWillStartHandler.bind(this));
    }

    async onWillStartHandler() {
        // Cart Qty should not change while the dialog is opened.
        this.cartQty = parseInt(sessionStorage.getItem("website_sale_cart_quantity"));
        if (!this.cartQty) {
            this.cartQty = await rpc("/shop/cart/quantity");
        }
        // Get required information about the order
        this.content = await rpc("/my/orders/reorder_modal_content", {
            order_id: this.props.orderId,
            access_token: this.props.accessToken,
        });
        // Get required information about each products
        for (const product of this.content.products) {
            product.debouncedLoadProductCombinationInfo = debounceFn(() => {
                this.loadProductCombinationInfo(product).then(this.render.bind(this));
            }, 200);
        }
    }

    get total() {
        return this.content.products.reduce((total, product) => {
            if (product.add_to_cart_allowed) {
                total += product.combinationInfo.price * product.qty;
            }
            return total;
        }, 0);
    }

    get hasBuyableProducts() {
        return this.content.products.some((product) => product.add_to_cart_allowed);
    }

    async loadProductCombinationInfo(product) {
        product.combinationInfo = await rpc("/website_sale/get_combination_info", {
            product_template_id: product.product_template_id,
            product_id: product.product_id,
            combination: product.combination,
            add_qty: product.qty,
            context: {
                website_sale_no_images: true,
            },
        });
    }

    getWarningForProduct(product) {
        if (!product.add_to_cart_allowed) {
            return _t("This product is not available for purchase.");
        }
        return false;
    }

    changeProductQty(product, newQty) {
        const productNewQty = Math.max(0, newQty);
        const qtyChanged = productNewQty !== product.qty;
        product.qty = productNewQty;
        this.render(true);
        if (!qtyChanged) {
            return;
        }
        product.debouncedLoadProductCombinationInfo();
    }

    onChangeProductQtyInput(ev, product) {
        const newQty = parseFloat(ev.target.value) || product.qty;
        this.changeProductQty(product, newQty);
    }

    async confirmReorder(ev) {
        if (this.confirmed) {
            return;
        }
        this.confirmed = true;
        const onConfirm = async () => {
            await this.addProductsToCart();
            window.location = "/shop/cart";
        };
        if (this.cartQty) {
            // Open confirmation modal
            this.dialogService.add(ReorderConfirmationDialog, {
                body: _t("Do you wish to clear your cart before adding products to it?"),
                confirm: async () => {
                    await rpc("/shop/cart/clear");
                    await onConfirm();
                },
                cancel: onConfirm,
            });
        } else {
            await onConfirm();
        }
    }

    async addProductsToCart() {
        let promises = [];
        for (const product of this.content.products) {
            if (!product.add_to_cart_allowed) {
                continue;
            }

            promises.push(this.websiteSale.addToCart({
                productTemplateId: product.product_template_id,
                productId: product.product_id,
                quantity: product.qty,
                productCustomAttributeValues: product.product_custom_attribute_values,
                noVariantAttributeValues: product.no_variant_attribute_value_ids,
            }, {
                isBuyNow: true,
                redirectToCart: false,
                isConfigured: true,
            }));
        }
        return Promise.all(promises);
    }
}
