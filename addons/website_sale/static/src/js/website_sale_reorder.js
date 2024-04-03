/** @odoo-module **/

import { debounce as debounceFn } from "@web/core/utils/timing";
import publicWidget from "web.public.widget";
import { localization as l10n } from "@web/core/l10n/localization";
import { ComponentWrapper } from "web.OwlCompatibility";
import { intersperse, nbsp } from "@web/core/utils/strings";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

/**
 * Inserts "thousands" separators in the provided number.
 *
 * @private
 * @param {string} string representing integer number
 * @param {string} [thousandsSep=","] the separator to insert
 * @param {number[]} [grouping=[]]
 *   array of relative offsets at which to insert `thousandsSep`.
 *   See `strings.intersperse` method.
 * @returns {string}
 */
function insertThousandsSep(number, thousandsSep = ",", grouping = []) {
    const negative = number[0] === "-";
    number = negative ? number.slice(1) : number;
    return (negative ? "-" : "") + intersperse(number, grouping, thousandsSep);
}

export function formatFloat(value, digits = 2) {
    if (value === false) {
        return "";
    }
    const grouping = l10n.grouping;
    const thousandsSep = l10n.thousandsSep;
    const decimalPoint = l10n.decimalPoint;
    let precision = digits;
    const formatted = (value || 0).toFixed(precision).split(".");
    formatted[0] = insertThousandsSep(formatted[0], thousandsSep, grouping);
    return formatted[1] ? formatted.join(decimalPoint) : formatted[0];
}

export function formatMonetary(value, currency) {
    // Monetary fields want to display nothing when the value is unset.
    // You wouldn't want a value of 0 euro if nothing has been provided.
    if (value === false) {
        return "";
    }

    const digits = (currency && currency.decimal_places) || 2;

    let formattedValue = formatFloat(value, digits);

    if (!currency) {
        return formattedValue;
    }
    const formatted = [currency.symbol, formattedValue];
    if (currency.position === "after") {
        formatted.reverse();
    }
    return formatted.join(nbsp);
}

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
        const dialogWrapper = new ComponentWrapper(this, ReorderDialogWrapper, {
            orderId: orderId,
            accessToken: urlSearchParams.get("access_token"),
        });
        dialogWrapper.mount(document.body);
    },
});

import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

const { Component, onRendered, onWillStart, xml } = owl;

// Reorder Dialog

export class ReorderDialogWrapper extends Component {
    setup() {
        this.dialogService = useService("dialog");

        onRendered(() => {
            this.dialogService.add(ReorderDialog, this.props);
        });
    }
}
ReorderDialogWrapper.template = xml``;

export class ReorderConfirmationDialog extends ConfirmationDialog {}
ReorderConfirmationDialog.template = "website_sale.ReorderConfirmationDialog";

export class ReorderDialog extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.formatMonetary = formatMonetary;

        onWillStart(this.onWillStartHandler.bind(this));
    }

    async onWillStartHandler() {
        // Cart Qty should not change while the dialog is opened.
        this.cartQty = parseInt(sessionStorage.getItem("website_sale_cart_quantity"));
        if (!this.cartQty) {
            this.cartQty = await this.rpc("/shop/cart/quantity");
        }
        // Get required information about the order
        this.content = await this.rpc("/my/orders/reorder_modal_content", {
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
        product.combinationInfo = await this.rpc("/sale/get_combination_info_website", {
            product_template_id: product.product_template_id,
            product_id: product.product_id,
            combination: product.combination,
            add_qty: product.qty,
            pricelist_id: false,
            context: {
                website_sale_no_images: true,
            },
        });
    }

    getWarningForProduct(product) {
        if (!product.add_to_cart_allowed) {
            return this.env._t("This product is not available for purchase.");
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
                body: this.env._t("Do you wish to clear your cart before adding products to it?"),
                confirm: async () => {
                    await this.rpc("/shop/cart/clear");
                    await onConfirm();
                },
                cancel: onConfirm,
            });
        } else {
            await onConfirm();
        }
    }

    async addProductsToCart() {
        for (const product of this.content.products) {
            if (!product.add_to_cart_allowed) {
                continue;
            }
            await this.rpc("/shop/cart/update_json", {
                product_id: product.product_id,
                add_qty: product.qty,
                no_variant_attribute_values: JSON.stringify(product.no_variant_attribute_values),
                product_custom_attribute_values: JSON.stringify(product.product_custom_attribute_values),
            });
        }
    }
}
ReorderDialog.props = {
    close: Function,
    orderId: Number,
    accessToken: String,
};
ReorderDialog.components = {
    Dialog,
};
ReorderDialog.template = "website_sale.ReorderModal";
