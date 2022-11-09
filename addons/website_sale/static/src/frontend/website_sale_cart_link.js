/** @odoo-module **/

import { registry, Widget } from "web.public.widget";
import { _t } from "web.core";

/**
 * This widget is responsible for the following:
 *  - Add a popover upon hoverig on the cart icon in the header.
 *  - Make sure the cart quantity stays correct.
 */
export const WebsiteSaleCartLink = Widget.extend({
    selector: '#top_menu a[href$="/shop/cart"]',
    events: {
        mouseenter: "_onMouseEnter",
        mouseleave: "_onMouseLeave",
        click: "_onClick",
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._popoverRPC = null;
        this._onVisibilityChange = this._onVisibilityChange.bind(this);
    },
    /**
     * @override
     */
    willStart() {
        return Promise.all([this._super.apply(this, arguments), this._updateCartQuantityValue()]);
    },
    /**
     * @override
     */
    start: function () {
        this.popover = new Popover(this.el, {
            trigger: "manual",
            animation: true,
            html: true,
            title: () => _t("My Cart"),
            container: "body",
            placement: "auto",
            template:
                '<div class="popover mycart-popover" role="tooltip"><div class="tooltip-arrow"></div><h3 class="popover-header"></h3><div class="popover-body"></div></div>',
        });
        this.tipLeaveEventHandler = () => this.$el.trigger("mouseleave");
        window.addEventListener("visibilitychange", this._onVisibilityChange);
        this._updateCartQuantityText();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy() {
        window.removeEventListener("visibilitychange", this._onVisibilityChange);
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onMouseEnter: function (ev) {
        this.hovered = true;
        clearTimeout(this.timeout);
        this.popover.hide();
        this.timeout = setTimeout(() => {
            if (!this.hovered || $(".mycart-popover:visible").length) {
                return;
            }
            this._popoverRPC = $.get("/shop/cart", {
                type: "popover",
            }).then((data) => {
                this.popover._config.content = data;
                this.popover.setContent(this.popover.getTipElement());
                this.popover.show();
                this.popover.tip.addEventListener("mouseleave", this.tipLeaveEventHandler);
                const cartQtyEl = this.popover.tip.querySelector(".o_wsale_cart_quantity");
                if (cartQtyEl) {
                    this.cartQty = +cartQtyEl.innerText;
                    sessionStorage.setItem("website_sale_cart_quantity", this.cartQty);
                    this._updateCartQuantityText();
                }
            });
        }, 300);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseLeave: function (ev) {
        this.hovered = false;
        setTimeout(() => {
            if ((this.popover.tip && this.popover.tip.matches(":hover")) || this.el.matches(":hover")) {
                return;
            }
            if (this.popover.tip) {
                this.popover.tip.removeEventListener("mouseleave", this.tipLeaveEventHandler);
            }
            this.popover.hide();
        }, 1000);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClick: function (ev) {
        // When clicking on the cart link, prevent any popover to show up (by
        // clearing the related setTimeout) and, if a popover rpc is ongoing,
        // wait for it to be completed before going to the link's href. Indeed,
        // going to that page may perform the same computation the popover rpc
        // is already doing.
        clearTimeout(this.timeout);
        if (this._popoverRPC && this._popoverRPC.state() === "pending") {
            ev.preventDefault();
            var href = ev.currentTarget.href;
            this._popoverRPC.then(function () {
                window.location.href = href;
            });
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onVisibilityChange(ev) {
        if (ev.target.visibilityState === "visible") {
            this._updateCartQuantityValue().then(this._updateCartQuantityText.bind(this));
        }
    },
    /**
     * @private
     */
    async _updateCartQuantityValue() {
        if ("website_sale_cart_quantity" in sessionStorage) {
            this.cartQty = sessionStorage.getItem("website_sale_cart_quantity");
        }
        if (this.el.querySelector(".my_cart_quantity").innerText != this.cartQty) {
            return this._rpc({ route: "/shop/cart/quantity" }).then((cartQty) => {
                this.cartQty = cartQty;
                sessionStorage.setItem("website_sale_cart_quantity", this.cartQty);
            });
        }
    },
    /**
     * @private
     */
    _updateCartQuantityText() {
        if (this.cartQty !== undefined) {
            this.el.querySelector(".my_cart_quantity").innerText = this.cartQty;
        }
    },
});

registry.WebsiteSaleCartLink = WebsiteSaleCartLink;
