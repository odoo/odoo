import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { Mutex } from "@web/core/utils/concurrency";
import { renderToString } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";
import VariantMixin from "@website_sale/js/sale_variant_mixin";
import website_sale_utils from "@website_sale/js/website_sale_utils";
import { redirect } from "@web/core/utils/urls";
import { slideToggle } from "@web/core/utils/slide";

const cartHandlerMixin = website_sale_utils.cartHandlerMixin;

// VariantMixin events are overridden on purpose here
// to avoid registering them more than once since they are already registered
// in website_sale.js
var ProductComparison = publicWidget.Widget.extend(VariantMixin, {
    template: 'product_comparison_template',
    events: {
        'click .o_product_panel_header': '_onClickPanelHeader',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this.product_data = {};
        this.comparelist_product_ids = JSON.parse(cookie.get('comparelist_product_ids') || '[]');
        this.product_compare_limit = 4;
        this.guard = new Mutex();
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        self._loadProducts(this.comparelist_product_ids).then(function () {
            self._updateContent('hide');
        });
        self._updateComparelistView();

        new Popover(this.el.querySelector("#comparelist .o_product_panel_header"), {
            trigger: 'manual',
            animation: true,
            html: true,
            title: function () {
                return _t("Compare Products");
            },
            container: '.o_product_feature_panel',
            placement: 'top',
            template: renderToString('popover'),
            content: function () {
                return document.querySelector("#comparelist .o_product_panel_content").innerHTML;
            },
        });
        // We trigger a resize to launch the event that checks if this element hides
        // a button when the page is loaded.
        window.dispatchEvent(new Event("resize"));

        this.onClickFeaturePanel = (ev) => {
            if (ev.target.closest("a")?.matches(".o_remove")) {
                ev.preventDefault();
                self._removeFromComparelist(ev);
            }
        };
        this.onClickCompareListRemove = (ev) => {
            self._removeFromComparelist(ev);
            self.guard.exec(function () {
                const newLink =
                    "/shop/compare?products=" +
                    encodeURIComponent(self.comparelist_product_ids);
                const url =
                    Object.keys(self.comparelist_product_ids || {}).length === 0
                        ? "/shop"
                        : newLink;
                redirect(url);
            });
        };
        document.body
            .querySelector(".o_product_feature_panel")
            ?.addEventListener("click", this.onClickFeaturePanel);

        document.body.querySelectorAll(".o_comparelist_remove").forEach((el) => {
            el.addEventListener("click", this.onClickCompareListRemove);
        });

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        document.body
            .querySelector(".o_product_feature_panel")
            ?.removeEventListener("click", this.onClickFeaturePanel);

        document.body.querySelectorAll(".o_comparelist_remove").forEach((el) => {
            el.removeEventListener("click", this.onClickCompareListRemove);
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Element} elem
     */
    handleCompareAddition(elem) {
        var self = this;
        if (this.comparelist_product_ids.length < this.product_compare_limit) {
            let productId = parseInt(elem.dataset?.productProductId);
            if (elem.classList.contains("o_add_compare_dyn")) {
                productId = elem.parentNode.querySelector(".product_id")?.value;
                if (!productId) { // case List View Variants
                    productId = elem.parentNode.querySelector("input:checked").value;
                }
            }

            let formEl = elem.closest("form");
            formEl = formEl ? formEl : this.el.querySelector("#product_details > form");
            this.selectOrCreateProduct(
                formEl,
                productId,
                formEl.querySelector(".product_template_id")?.value
            ).then(function (productId) {
                productId = parseInt(productId, 10) || parseInt(elem.dataset?.productProductId, 10);
                if (!productId) {
                    return;
                }
                self._addNewProducts(productId).then(function () {
                    website_sale_utils.animateClone(
                        document.querySelector("#comparelist .o_product_panel_header"),
                        elem.closest("form"),
                        -50,
                        10
                    );
                });
            });
        } else {
            this.el
                .querySelectorAll(".o_comparelist_limit_warning")
                .forEach((el) => (el.style.display = ""));
            const popover = Popover.getOrCreateInstance(
                this.el.querySelector("#comparelist .o_product_panel_header")
            );
            popover.show();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _loadProducts: function (product_ids) {
        var self = this;
        const cookies = JSON.parse(cookie.get('comparelist_product_ids') || '[]');
        if (product_ids.length == 0 && cookies.length == 0) {
            return Promise.resolve(true);
        }
        return rpc('/shop/get_product_data', {
            product_ids: product_ids,
            cookies: cookies,
        }).then(function (data) {
            self.comparelist_product_ids = JSON.parse(data.cookies);
            delete data.cookies;
            Object.values(data).forEach((product) => {
                self.product_data[product.product.id] = product;
            });
            if (product_ids.length > Object.keys(data).length) {
                /* If some products have been archived
                they are not displayed but the count & cookie
                need to be updated.
                */
                self._updateCookie();
            }
        });
    },
    /**
     * @private
     */
    _togglePanel: function () {
        const popover = Popover.getOrCreateInstance(
            this.el.querySelector("#comparelist .o_product_panel_header")
        );
        popover.toggle();
    },
    /**
     * @private
     */
    _addNewProducts: function (product_id) {
        return this.guard.exec(this._addNewProductsImpl.bind(this, product_id));
    },
    _addNewProductsImpl: function (product_id) {
        var self = this;
        document.querySelector(".o_product_feature_panel").classList.add("d-md-block");
        if (!self.comparelist_product_ids.includes(product_id)) {
            self.comparelist_product_ids.push(product_id);
            if (Object.prototype.hasOwnProperty.call(self.product_data, product_id)) {
                self._updateContent();
            } else {
                return self._loadProducts([product_id]).then(function () {
                    self._updateContent();
                    self._updateCookie();
                });
            }
        }
        self._updateCookie();
    },
    /**
     * @private
     */
    _updateContent: function (force) {
        var self = this;
        this.el
            .querySelectorAll(".o_comparelist_products .o_product_row")
            ?.forEach((el) => el.remove());
        this.comparelist_product_ids.forEach((res) => {
            if (self.product_data.hasOwnProperty(res)) {
                // It is possible that we do not have the required product_data for all IDs in
                // comparelist_product_ids
                const parser = new DOMParser();
                const template = parser.parseFromString(self.product_data[res].render, "text/html")
                    .body.firstChild;
                document.querySelector(".o_comparelist_products")?.append(template);
            }
        });
        const popover = Popover.getOrCreateInstance(
            this.el.querySelector("#comparelist .o_product_panel_header")
        );
        if (force !== 'hide' && (this.comparelist_product_ids.length > 1 || force === 'show')) {
            popover.show();
        } else {
            popover.hide();
        }
    },
    /**
     * @private
     */
    _removeFromComparelist: function (e) {
        this.guard.exec(this._removeFromComparelistImpl.bind(this, e));
    },
    _removeFromComparelistImpl: function (e) {
        const target = e.target.closest(".o_comparelist_remove, .o_remove");
        this.comparelist_product_ids = this.comparelist_product_ids.filter(
            (comp) => comp !== parseInt(target.dataset.product_product_id)
        );
        target.closest(".o_product_row")?.remove();
        this._updateCookie();
        this.el
            .querySelectorAll(".o_comparelist_limit_warning")
            .forEach((el) => (el.style.display = "none"));
        this._updateContent('show');
    },
    /**
     * @private
     */
    _updateCookie: function () {
        cookie.set('comparelist_product_ids', JSON.stringify(this.comparelist_product_ids), 24 * 60 * 60 * 365, 'required');
        this._updateComparelistView();
    },
    /**
     * @private
     */
    _updateComparelistView: function () {
        this.el.querySelector(".o_product_circle").textContent =
            this.comparelist_product_ids.length;
        this.el.querySelector(".o_comparelist_button").classList.remove("d-md-block");
        if (Object.keys(this.comparelist_product_ids || {}).length === 0) {
            document.querySelector(".o_product_feature_panel").classList.remove("d-md-block");
        } else {
            document.querySelector(".o_product_feature_panel").classList.add("d-md-block");
            this.el
                .querySelectorAll(".o_comparelist_products")
                .forEach((el) => el.classList.add("d-md-block"));
            if (this.comparelist_product_ids.length >=2) {
                this.el
                    .querySelectorAll(".o_comparelist_button")
                    .forEach((el) => el.classList.add("d-md-block"));
                this.el
                    .querySelectorAll(".o_comparelist_button a")
                    .forEach((el) =>
                        el.setAttribute(
                            "href",
                            "/shop/compare?products=" +
                                encodeURIComponent(this.comparelist_product_ids)
                        )
                    );
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickPanelHeader: function () {
        this._togglePanel();
    },
});

publicWidget.registry.ProductComparison = publicWidget.Widget.extend(cartHandlerMixin, {
    selector: '.js_sale',
    events: {
        'click .o_add_compare, .o_add_compare_dyn': '_onClickAddCompare',
        'click #o_comparelist_table tr': '_onClickComparelistTr',
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this.productComparison = new ProductComparison(this);
        this.getRedirectOption();
        // During the removal of jQuery, we discovered that the "_onFormSubmit" event needs to be dispatched via
        // JavaScript in the "Website_sale.js" file. As a result, we need to bind this event using JavaScript's
        // addEventListener method.
        this.boundedSubmitForm = this._onFormSubmit.bind(this);
        this.el.querySelectorAll(".o_add_cart_form_compare").forEach((el) => {
            el.addEventListener("submit", this.boundedSubmitForm);
        });
        return Promise.all([def, this.productComparison.appendTo(this.el)]);
    },

    destroy() {
        this._super(...arguments);
        this.el.querySelector(".o_add_cart_form_compare")?.removeEventListener("submit", this.boundedSubmitForm);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickAddCompare: function (ev) {
        this.productComparison.handleCompareAddition(ev.currentTarget);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickComparelistTr: function (ev) {
        const currentTargetEl = ev.currentTarget;
        const children = currentTargetEl.getAttribute("data-target")?.children();
        (children || []).forEach((child) => slideToggle(child, 100));
        currentTargetEl
            .querySelectorAll(".fa-chevron-circle-down, .fa-chevron-circle-right")
            .forEach((el) => {
                el.classList.toggle("fa-chevron-circle-down");
                el.classList.toggle("fa-chevron-circle-right");
            });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFormSubmit(ev) {
        ev.preventDefault();
        const formEl = ev.currentTarget;
        const cellIndex = ev.currentTarget.closest("td").cellIndex;
        this.getCartHandlerOptions(ev);
        // Override product image container for animation.
        this.itemImgContainerEl =
            this.el.querySelector("#o_comparelist_table tr").children[cellIndex];
        const inputProductEl = formEl.querySelector('input[type="hidden"][name="product_id"]');
        const productId = parseInt(inputProductEl.value);
        if (productId) {
            const productTrackingInfo = inputProductEl.dataset.productTrackingInfo;
            if (productTrackingInfo) {
                productTrackingInfo.quantity = 1;
                inputProductEl.dispatchEvent(
                    new CustomEvent("add_to_cart_event", { detail: productTrackingInfo })
                );
            }
            return this.addToCart(this._getAddToCartParams(productId, formEl));
        }
    },
    /**
     * Get the addToCart Params
     *
     * @param {number} productId
     * @param {Element} formEl
     * @override
     */
    _getAddToCartParams(productId, formEl) {
        return {
            product_id: productId,
            add_qty: 1,
        };
    }
});
export default ProductComparison;
