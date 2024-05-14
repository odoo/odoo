/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";

// Widget responsible for opening the modal

publicWidget.registry.PortalLoyaltyWidget = publicWidget.Widget.extend({
    selector: "#o_modal_test_selector",
    events: {
        "click .o_modal_test_event_click": "_onPortalLoyalty",
    },

    _onPortalLoyalty(ev) {
        console.log("___________________________________");
        const title = ev.currentTarget.dataset.title;
        const points = ev.currentTarget.dataset.points;
        const pointName = ev.currentTarget.dataset.pointName;
        const rewardId = parseInt(ev.currentTarget.dataset.rewardId);
        console.log("title:");
        console.log(title);
        console.log("rewardId:");
        console.log(rewardId);
        if (!rewardId || !title) {
            return;
        }
        // Open the modal
        this.call("dialog", "add", PortalLoyalty, {
            title: title,
            rewardId: rewardId,
            points: points,
            pointName: pointName,
        });
    },
});

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";


export class PortalLoyalty extends Component {
    static components = { Dialog };
    static template = 'portal_loyalty_modal.LoyaltyModal';
    static props = {
        title: String,
        rewardId: Number,
        // partnerId: Number,
    };

    setup() {
        this.title = this.props.title;
        this.points = this.props.points;
        this.pointName = this.props.pointName;
        this.state = useState({
            rewards: [],
        });

        // onWillStart(this.onWillStartHandler.bind(this));

        // onWillStart(async () => {
        //     this.state.rewards = await this._loadData(this.props.edit);
        // });
    }


    async topUpNow(ev) {
        console.log("Hello World !!")
    }

    // async _loadData(onlyMainProduct) {
    //     return rpc('/?????????/get_values', {
    //         quantity: this.props.quantity,
    //     });
    // }

    // async onWillStartHandler() {
    //     // Cart Qty should not change while the dialog is opened.
    //     this.cartQty = parseInt(sessionStorage.getItem("website_sale_cart_quantity"));
    //     if (!this.cartQty) {
    //         this.cartQty = await rpc("/shop/cart/quantity");
    //     }
    //     // Get required information about the order
    //     this.content = await rpc("/my/orders/reorder_modal_content", {
    //         order_id: this.props.rewardId,
    //         access_token: this.props.accessToken,
    //     });
    //     // Get required information about each products
    //     for (const product of this.content.products) {
    //         product.debouncedLoadProductCombinationInfo = debounceFn(() => {
    //             this.loadProductCombinationInfo(product).then(this.render.bind(this));
    //         }, 200);
    //     }
    // }
}

// export class ReorderDialog extends Component {
//     static template = "website_sale.ReorderModal";
//     static props = {
//         close: Function,
//         rewardId: Number,
//         accessToken: String,
//     };
//     static components = {
//         Dialog,
//     };

//     setup() {
//         this.orm = useService("orm");
//         this.dialogService = useService("dialog");
//         this.formatCurrency = formatCurrency;

//         onWillStart(this.onWillStartHandler.bind(this));
//     }

//     async onWillStartHandler() {
//         // Cart Qty should not change while the dialog is opened.
//         this.cartQty = parseInt(sessionStorage.getItem("website_sale_cart_quantity"));
//         if (!this.cartQty) {
//             this.cartQty = await rpc("/shop/cart/quantity");
//         }
//         // Get required information about the order
//         this.content = await rpc("/my/orders/reorder_modal_content", {
//             order_id: this.props.rewardId,
//             access_token: this.props.accessToken,
//         });
//         // Get required information about each products
//         for (const product of this.content.products) {
//             product.debouncedLoadProductCombinationInfo = debounceFn(() => {
//                 this.loadProductCombinationInfo(product).then(this.render.bind(this));
//             }, 200);
//         }
//     }

//     get total() {
//         return this.content.products.reduce((total, product) => {
//             if (product.add_to_cart_allowed) {
//                 total += product.combinationInfo.price * product.qty;
//             }
//             return total;
//         }, 0);
//     }

//     get hasBuyableProducts() {
//         return this.content.products.some((product) => product.add_to_cart_allowed);
//     }

//     async loadProductCombinationInfo(product) {
//         product.combinationInfo = await rpc("/website_sale/get_combination_info", {
//             product_template_id: product.product_template_id,
//             product_id: product.product_id,
//             combination: product.combination,
//             add_qty: product.qty,
//             context: {
//                 website_sale_no_images: true,
//             },
//         });
//     }

//     getWarningForProduct(product) {
//         if (!product.add_to_cart_allowed) {
//             return _t("This product is not available for purchase.");
//         }
//         return false;
//     }

//     changeProductQty(product, newQty) {
//         const productNewQty = Math.max(0, newQty);
//         const qtyChanged = productNewQty !== product.qty;
//         product.qty = productNewQty;
//         this.render(true);
//         if (!qtyChanged) {
//             return;
//         }
//         product.debouncedLoadProductCombinationInfo();
//     }

//     onChangeProductQtyInput(ev, product) {
//         const newQty = parseFloat(ev.target.value) || product.qty;
//         this.changeProductQty(product, newQty);
//     }

//     async confirmReorder(ev) {
//         if (this.confirmed) {
//             return;
//         }
//         this.confirmed = true;
//         const onConfirm = async () => {
//             await this.addProductsToCart();
//             window.location = "/shop/cart";
//         };
//         if (this.cartQty) {
//             // Open confirmation modal
//             this.dialogService.add(ReorderConfirmationDialog, {
//                 body: _t("Do you wish to clear your cart before adding products to it?"),
//                 confirm: async () => {
//                     await rpc("/shop/cart/clear");
//                     await onConfirm();
//                 },
//                 cancel: onConfirm,
//             });
//         } else {
//             await onConfirm();
//         }
//     }

//     async addProductsToCart() {
//         for (const product of this.content.products) {
//             if (!product.add_to_cart_allowed) {
//                 continue;
//             }
//             await rpc("/shop/cart/update_json", {
//                 product_id: product.product_id,
//                 add_qty: product.qty,
//                 no_variant_attribute_value_ids: product.no_variant_attribute_value_ids,
//                 product_custom_attribute_values: JSON.stringify(product.product_custom_attribute_values),
//                 display: false,
//             });
//         }
//     }
// }
