/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
// import { formatMonetary } from "@web/views/fields/formatters";
import { formatCurrency, getCurrency } from "@web/core/currency";
import { formatDate, parseDate } from "@web/core/l10n/dates";

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
        const couponId = parseInt(ev.currentTarget.dataset.couponId);
        const value = ev.currentTarget.dataset.value;
        console.log("value:");
        console.log(value);
        console.log("title:");
        console.log(title);
        console.log("couponId:");
        console.log(couponId);
        console.log("rewardId:");
        console.log(rewardId);
        if (!rewardId || !title) {
            return;
        }
        // Open the modal
        this.call("dialog", "add", PortalLoyalty, {
            title: title,
            rewardId: rewardId,
            couponId: couponId,
            points: points,
            pointName: pointName,
        });
    },
});

import { Dialog } from "@web/core/dialog/dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import {
    Component,
    useState,
    onWillStart,
} from "@odoo/owl";

export class PortalLoyalty extends Component {
    static components = {
        Dialog,
        Dropdown,
        DropdownItem,
    };
    static template = 'portal_loyalty_modal.LoyaltyModal';
    static props = {
        title: String,
        rewardId: Number,
        couponId: Number,
        points: Number,
        pointName: String,
        historyId: Number,
        // partnerId: Number,
    };

    setup() {
        this.title = this.props.title;
        this.points = this.props.points;
        this.pointName = this.props.pointName;
        this.topUpValues = [25, 50, 100, 200, 42.4242];
        this.state = useState({
            currencyId: null,
            history: [],
            topUpIndex: 0,
        });

        onWillStart(this.onWillStartHandler.bind(this));

        // onWillStart(async () => {
        //     this.state.rewards = await this._loadData(this.props.edit);
        // });
    }

    async topUpNow() {
        console.log("Top-Up for", this.topUpValues[this.state.topUpIndex], this.props.pointName);
    }

    formatDate(date) {
        return formatDate(parseDate(date));
    }

    formatPoints(points){
        if (this.pointName == getCurrency(this.state.currencyId).symbol)
            return formatCurrency(points, this.state.currencyId);
        if (points % 1 === 0)
            return points.toString() + this.pointName;
        return points.toFixed(2) + this.pointName;
    }

    // async _loadData(onlyMainProduct) {
    //     return rpc('/?????????/get_values', {
    //         quantity: this.props.quantity,
    //     });
    // }

    onChangetopUpValue(ev) {
        const value = JSON.parse(ev.target.value);
        this.state.topUpIndex = this.topUpValues.indexOf(value);
    }

    get topUpValue() {
        return this.formatPoints(this.topUpValues[this.state.topUpIndex])
    }

    async onWillStartHandler() {
        console.log('this.props.couponId: ');
        console.log(this.props.couponId);
        const { currencyId, history } = await rpc("/my/rewards/history", {
            coupon_id: this.props.couponId,
        });
        this.state.history = history;
        this.state.currencyId = currencyId;
        console.log('this.state.history: ');
        console.log(this.state.history);
        console.log('this.state.currencyId: ');
        console.log(this.state.currencyId);

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
    }
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
