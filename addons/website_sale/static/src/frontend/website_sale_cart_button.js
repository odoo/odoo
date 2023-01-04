/** @odoo-module **/

import { registry, Widget } from "web.public.widget";
import { _t } from "web.core";

/**
 * Interface for widgets to implement to be able to use
 * add to cart buttons.
 */
export const WebsiteSaleCartButtonParent = {
    // A cart widget will be initialised for each element matching this selector.
    addToCartButtonSelector: ".o_wsale_add_to_cart",
    // Additional selector used for the click event of the button's widget.
    cartButtonAdditionalSelector: undefined,
    custom_events: {
        get_product_info: "getProductInfo",
    },

    start() {
        const result = this._super(...arguments);
        this.cartButtons = [];
        const buttons = this.el.querySelectorAll(this.addToCartButtonSelector);
        buttons.forEach((btn) => {
            const cartButton = new OwnedWebsiteSaleCartButton(this, {
                buttonSelector: this.cartButtonAdditionalSelector,
            });
            this.cartButtons.push(cartButton);
            cartButton.attachTo(btn);
        });
        return result;
    },

    destroy() {
        const result = this._super(...arguments);
        this.cartButtons.forEach((btn) => btn.destroy());
        this.cartButtons = [];
        return result;
    },

    /**
     * Called when the button needs more information about the current context.
     * The resolve function should be called with the product information.
     *
     * @param {HTMLElement} ev.data.el Element of the button requesting the information.
     * @param {HTMLElement} ev.data.target Target of the original event.
     * @param {HTMLElement} ev.data.currentTarget CurrentTarget of the original event.
     * @param {Function} ev.data.resolve Caller promise to be resolved.
     */
    async getProductInfo(ev) {
        throw new Error("not implemented by parent");
    },
};

/**
 * Add to cart button which requires a parent to get all
 * the options before being able to execute the action.
 *
 * The button is not aware of it's context until it requests the information from the parent.
 */
export const OwnedWebsiteSaleCartButton = Widget.extend({
    events: {
        click: "onClick",
    },

    init(parent, options) {
        const result = this._super(...arguments);
        if (options && options.buttonSelector) {
            // Remove base event and add our more specific one.
            this.events = {
                ...this.events,
                [`click ${options.buttonSelector}`]: "onClick",
            };
            delete this.events.click;
        }
        return result;
    },

    /**
     * Requests information about the product from the parent.
     *
     * Expected keys in the return value (optional unless specified) [default value]:
     *  - product_id (required)
     *  - product_template_id
     *  - add_qty [1]
     *  - combination
     *  - pricelist_id
     *
     * @returns {Promise<Object>} Information about the product to add.
     */
    async getProductInfo({ currentTarget, target }) {
        return new Promise((resolve) => {
            const data = {
                el: this.el,
                target,
                currentTarget,
                resolve,
            };
            this.trigger_up("get_product_info", data);
        });
    },

    async onClick(ev) {
        const productInfo = await this.getProductInfo(ev);
        // TODO: we actually need either product_id or template + combination; both are fine
        if (!productInfo.product_id) {
            throw new Error(_t("The button does not have enough information to be able to add the product to cart."));
        }
        if (!productInfo.add_qty) {
            productInfo.add_qty = 1;
        }
        // TODO: impl
        console.log(productInfo);
    },
});

/**
 * Standalone add to cart button, no parent required.
 *
 * The button is aware of it's own context.
 */
export const StandaloneWebsiteSaleCartButton = OwnedWebsiteSaleCartButton.extend({
    selector: ".o_wsale_add_to_cart.o_wsale_add_to_cart_standalone",

    /**
     * Deduce the product's information from the arch of the element.
     *
     * @override
     */
    getProductInfo() {
        return {
            product_id: this.el.dataset.productId,
            product_template_id: this.el.dataset.productTemplateId,
        };
    },
});
registry.StandaloneWebsiteSaleCartButton = StandaloneWebsiteSaleCartButton;
