import { EventBus, markup, proxy } from "@odoo/owl";
import {
    ComboConfiguratorDialog
} from '@sale/js/combo_configurator_dialog/combo_configurator_dialog';
import { ProductCombo } from '@sale/js/models/product_combo';
import {
    ProductConfiguratorDialog
} from '@sale/js/product_configurator_dialog/product_configurator_dialog';
import { getConfiguredPtavs, serializeComboItem } from '@sale/js/sale_utils';
import { browser } from '@web/core/browser/browser';
import { serializeDateTime } from '@web/core/l10n/dates';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Mutex } from "@web/core/utils/concurrency";
import { redirect } from '@web/core/utils/urls';
import {
    CartNotificationContainer
} from '@website_sale/js/cart_notification/cart_notification_container/cart_notification_container';
import wSaleUtils from "@website_sale/js/website_sale_utils";

const { DateTime } = luxon;
const AUTOCLOSE_NOTIFICATION_DELAY = 4000;

/**
 * @typedef {Object} CustomAttributeValues
 * @property {Number} custom_product_template_attribute_value_id
 * @property {String} custom_value
 */

/**
 * Single source of truth for the eCommerce cart on the client side.
 *
 * The service has two responsibilities:
 *
 * 1. Cart actions, via {@link add} and {@link update}:
 *    - Opening the product/combo configurators if needed;
 *    - Adding products to the cart, or updating/removing existing lines;
 *    - Updating the cart count in the navbar;
 *    - Notifying the customer of successful additions and warnings;
 *    - Tracking the added/updated products.
 *
 * 2. Cart state, via {@link loadCart}:
 *    - The cart data (`lines`, `totals`, order `history` and `currency_id`) is fetched from
 *      `/shop/cart/data` and stored in the reactive {@link state} object;
 *    - The OWL cart components (`CartLines`, `CartTotal`, `CartSummary`, `CartQuickReorder`, ...)
 *      read from this shared state instead of each fetching their own data, and re-render
 *      automatically when it changes;
 *    - Cart updates reload the state once they are done, so that all components stay in sync
 *      without re-rendering server-side fragments. Additions don't, as most of them happen outside
 *      of the cart page: callers displaying the cart must reload it themselves.
 *
 * The service also exposes a {@link bus} on which the following events are triggered:
 *    - `cart_amount_changed`: triggered after a product is added, a cart line is updated, a code
 *      is applied or the delivery method is changed, with the new `[amount, minorAmount]` of the
 *      order as payload (e.g. used by the express checkout and the delivery methods of the
 *      checkout page).
 *
 * Override this class to implement additional checks or provide relevant information when
 * adding a product to the cart, or to extend the cart state.
 */
export class CartService {
    static dependencies = ["dialog", "public.interactions"];

    /**
     * Creates an instance of the service and initializes it using the {@link setup} method.
     *
     * The constructor delegates initialization to {@link setup} to handle wiring up dependencies,
     * setting up methods, and initializing global variables, as constructors themselves cannot be
     * patched.
     *
     * @returns {Object} - The initialized service object returned by {@link setup}.
     */
    constructor() {
        return this.setup(...arguments);
    }

    /**
     * Initializes the service wiring up dependencies, setting up methods and initializing global
     * variables.
     *
     * @param {import("@web/env").OdooEnv} _env - The environment object, not used here.
     * @param {import("services").ServiceFactories} services - An object containing instances of the
     *      required services specified in the {@link dependencies} array.
     *
     * @returns {Object} - An object exposing the public methods of the service.
     */
    setup(_env, services) {
        this.dialog = services.dialog;
        this.interactions = services["public.interactions"];
        this.rpc = rpc; // To be overridable in tests.
        this.notifications = proxy(new Set());
        this.bus = new EventBus();
        this.mutex = new Mutex();
        this.state = proxy({
            lines: {},
            totals: {},
            history: {},
            currency_id: false,
            is_quantity_view_active: false,
            is_wishlist_view_active: false,
            show_product_reference_price: false,
        });
        this.cartLoaded = false;

        // Register the notification container
        registry.category('main_components').add('CartNotificationContainer',
            {
                Component: CartNotificationContainer,
                props: { notifications: this.notifications },
            }
        );

        return {
            bus: this.bus,
            state: this.state,
            loadCart: (...args) => this.loadCart(...args),
            add: (...args) => this.add(...args),
            update: (...args) => this.update(...args),
            showWarning: (...args) => this.showWarning(...args),
        };
    }

    //--------------------------------------------------------------------------
    // Methods exposed by the service.
    //--------------------------------------------------------------------------

    /**
     * Load the cart data into the shared {@link state}.
     *
     * Call it in the `onWillStart` of components reading the state, and with `force=true` after
     * modifying the cart outside of this service (e.g. applying a promo code).
     *
     * The mutex serializes the loads: components mounting together trigger a single request, and
     * concurrent reloads can't apply outdated data.
     *
     * @param {Object} [options]
     * @param {Boolean} [options.force=false] - Whether to fetch the data even if it was already
     *      loaded.
     * @param {Boolean} [options.fromConfirmationPage=false] - Whether to load the last confirmed
     *      order (`sale_last_order_id`) instead of the current cart.
     * @param {Boolean} [options.withHistory=false] - Whether to also load the order history of the
     *      customer, used by the quick reorder.
     *
     * @returns {Promise<void>}
     */
    async loadCart({ force = false, fromConfirmationPage = false, withHistory = false } = {}) {
        await this.mutex.exec(
            async () => await this._loadCartData(force, fromConfirmationPage, withHistory)
        );
    }

    /**
     * Asynchronously adds a product to the shopping cart.
     *
     * @param {Object} product - The product details to add to the cart.
     * @param {Number} product.productTemplateId - The product template's id, as a
     *      `product.template` id.
     * @param {Number} [product.productId=undefined] - The product's id, as a `product.product` id.
     *      If not provided, selects the first available product or creates one if any attribute is
     *      dynamic.
     * @param {Number} [product.quantity=1] - The quantity of the product to add to the cart.
     *      Defaults to 1.
     * @param {Number} [product.uom_id=undefined] - The product's uom id, as a `uom.uom` id.
     *      If not provided, considers the product default uom.
     * @param {Number[]} [product.ptavs=[]] - The selected stored attribute(s), as a list of
     *      `product.template.attribute.value` ids.
     * @param {CustomAttributeValues[]} [product.productCustomAttributeValues=[]] - An
     *      array of objects representing custom attribute values for the product.
     * @param {Number[]} [product.noVariantAttributeValues=[]] - The selected non-stored
     *      attribute(s), as a list of `product.template.attribute.value` ids.
     * @param {Boolean} [product.isCombo=false] - Whether the product is part of a combo template.
     *      Defaults to false.
     * @param {...*} [product.rest] - Locally unused data sent to the controllers.
     * @param {Object} [options] - Define how to add products to the cart.
     * @param {Boolean} [options.isBuyNow=false] - Whether the product should be added immediately,
     *      bypassing optional configurations. Defaults to false.
     * @param {Boolean} [options.redirectToCart=isBuyNow] - Whether to redirect the customer to
     *      the cart once the product is added. Defaults to `isBuyNow`.
     * @param {Boolean} [options.showNotification=true] - Whether to show the cart notifications
     *      once the product is added.
     * @param {Boolean} [options.skipOrderAlert=false] - Whether to not store the warning on the
     *      order when it can't be attached to a line. Use it when the customer won't see the cart
     *      page right after, so that the warning isn't shown again there.
     * @param {Boolean} [options.renderShorterCartSummary=false] - Whether to render the shorter
     *      cart summary, e.g. when adding to an empty cart from the cart page.
     * @param {Boolean} [options.isConfigured=false] - Whether the product is already configured.
     *      Defaults to false.
     * @param {Boolean} [options.showQuantity=true] - Whether quantity selector should be shown
     *      Defaults to true.
     * @returns {Number} - The product's quantity added to the cart.
     */
    async add({
            productTemplateId,
            productId = undefined,
            quantity = 1,
            uomId = undefined,
            ptavs = [],
            productCustomAttributeValues = [],
            noVariantAttributeValues = [],
            isCombo = false,
            ...rest
        },
        {
            isBuyNow=false,
            isConfigured=false,
            redirectToCart=isBuyNow,
            showNotification=true,
            skipOrderAlert=false,
            renderShorterCartSummary=false,
            showQuantity=true,
        } = {},
    ) {
        const requestOptions = {
            shouldRedirectToCart: redirectToCart,
            showNotification: showNotification,
            skipOrderAlert: skipOrderAlert,
            renderShorterCartSummary: renderShorterCartSummary,
        };

        if (!productId && ptavs.length) {
            productId = await this.rpc('/sale/create_product_variant', {
                product_template_id: productTemplateId,
                product_template_attribute_value_ids: ptavs.concat(noVariantAttributeValues),
            })
        }

        if(isCombo) {
            const { combos, ...remainingData } = await this.rpc(
                '/website_sale/combo_configurator/get_data',
                {
                    product_tmpl_id: productTemplateId,
                    quantity: quantity,
                    // NOTE: no uom for combos on purpose
                    date: serializeDateTime(DateTime.now()),
                    ...rest
                }
            );
            const preselectedComboItems = combos
                .map(combo => new ProductCombo(combo))
                .map(combo => combo.preselectedComboItem)
                .filter(Boolean);

            const selectedComboItems = combos
                .map(combo => new ProductCombo(combo))
                .map(combo => combo.selectedComboItem)
                .filter(Boolean);

            // If the combo product is already fully configured (i.e. a combo item has been
            // preselected for each combo choice or all combo choices have been made from some
            // flow like quick reorder), then it can be added to the cart without opening the combo
            // configurator.
            if (
                preselectedComboItems.length === combos.length
                || selectedComboItems.length === combos.length
            ) {
                const comboItems = preselectedComboItems.length
                    ? preselectedComboItems
                    : selectedComboItems;

                return this._makeRequest({
                    productTemplateId: productTemplateId,
                    productId: productId,
                    quantity: remainingData.quantity,
                    uomId: uomId,
                    linked_products: comboItems.map(
                        (comboItem) => this._serializeComboItem(
                            comboItem, productTemplateId, remainingData.quantity
                        )
                    ),
                    ...requestOptions,
                    ...rest
                });
            }
            // If some combo choices need to be configured, open the combo configurator.
            return this._openComboConfigurator(
                productTemplateId,
                productId,
                combos.map(combo => new ProductCombo(combo)),
                remainingData,
                {
                    isBuyNow: isBuyNow,
                    showQuantity: showQuantity,
                },
                rest
            );
        }

        if (isBuyNow) {
            return this._makeRequest({
                productTemplateId,
                productId,
                quantity,
                uomId,
                productCustomAttributeValues,
                noVariantAttributeValues,
                ...requestOptions,
                ...rest
            });
        }

        const ptavIds = ptavs.concat(noVariantAttributeValues);
        const configDataParams = {
            product_template_id: productTemplateId,
            quantity: quantity,
            ptav_ids: ptavIds,
            product_uom_id: uomId,
            so_date: serializeDateTime(DateTime.now()),
            is_product_configured: isConfigured,
            ...rest
        };

        const result = await this.rpc('/website_sale/product_configurator/get_values', configDataParams);
        if (result.products) {
            const { products, optional_products, currency_id } = result;
            return this._openProductConfigurator(
                productTemplateId,
                products,
                optional_products,
                currency_id,
                productCustomAttributeValues,
                {
                    isBuyNow: isBuyNow,
                    isMainProductConfigurable: !isConfigured,
                    showQuantity: showQuantity,
                },
                rest
            );
        }

        return this._makeRequest({
            productTemplateId,
            productId,
            quantity,
            uomId,
            productCustomAttributeValues,
            noVariantAttributeValues,
            ...requestOptions,
            ...rest
        });
    }

    /**
     * Update the quantity of a cart line, or remove it if the quantity is 0.
     *
     * Once updated, the cart icon, the {@link state} and the express checkout amount (through the
     * `cart_amount_changed` event) are refreshed, and the update is tracked.
     *
     * @param {Object} line - The line to update.
     * @param {Number} line.lineId - The line's id, as a `sale.order.line` id.
     * @param {Number} [line.productId=undefined] - The line's product id, as a `product.product`
     *      id.
     * @param {Number} line.quantity - The new quantity of the line.
     * @param {Object} [options]
     * @param {Boolean} [options.fromCartPage=false] - Whether the update is done from the cart
     *      page. If so and the cart becomes empty, the page is reloaded to display the empty cart.
     *
     * @returns {Promise<void>}
     */
    async update({ lineId, productId = undefined, quantity }, { fromCartPage = false } = {}) {
        const data = await this.rpc("/shop/cart/update", {
            line_id: lineId,
            product_id: productId,
            quantity: quantity,
        });

        // If update was done from cart page, and cart is empty after update, refresh the page to
        // show the empty cart
        if (fromCartPage && !data.cart_quantity) {
            return redirect("/shop/cart");
        }

        this._updateCartIcon(data.cart_quantity);
        this.showWarning(data.warning);
        await this.loadCart({ force: true, withHistory: true });
        this.bus.trigger("cart_amount_changed", [data.amount, data.minor_amount]);

        if (data.tracking_info?.length) {
            wSaleUtils.dispatchTrackingEvent("update_cart_event", {
                currency: data.currency,
                items: data.tracking_info,
            });
        }
    }

    /**
     * Show a warning notification.
     *
     * @param {String} warningMessage
     *
     * @returns {void}
     */
    showWarning(warningMessage) {
        if (!warningMessage) return;
        this._showCartNotification({
            type: 'warning',
            data: { 'warning_message': warningMessage },
        });
    }

    //--------------------------------------------------------------------------
    // Configurators
    //--------------------------------------------------------------------------

    /**
     * Opens the combo configurator dialog.
     *
     * @param {Number} productTemplateId - The product template id, as a `product.template` id.
     * @param {Number} productId - The product's id, as a `product.product` id.
     * @param {ProductCombo[]} combos - The combos of the product.
     * @param {Object} remainingData - Other data needed to open the combo configurator.
     * @param {Number} remainingData.currency_id - The currency's id, as a `res.currency` id.
     * @param {String} remainingData.display_name - The name of the combo.
     * @param {Number} remainingData.price - The price of the combo.
     * @param {Number} remainingData.product_tmpl_id - The product template's id, as a
     *      `product.template` id.
     * @param {Number} remainingData.quantity - The quantity of the combo.
     * @param {Object} [options] - Define how to add products to the cart.
     * @param {Boolean} [options.isBuyNow] - Whether the product should be added immediately,
     *      bypassing optional configurations.
     * @param {Object} [additionalData] - Additional data sent to the controllers.
     *
     * @returns {Number} - The product's quantity added to the cart.
     */
    async _openComboConfigurator(
        productTemplateId,
        productId,
        combos,
        remainingData,
        options,
        additionalData
    ) {
        return await new Promise((resolve) => {
            this.dialog.add(ComboConfiguratorDialog, {
                combos: combos,
                ...remainingData,
                date: serializeDateTime(DateTime.now()),
                edit: false,
                isFrontend: true,
                options,
                ...additionalData,
                save: async (comboProductData, selectedComboItems, options) => {
                    resolve(this._makeRequest({
                        productTemplateId: productTemplateId,
                        productId: productId,
                        quantity: comboProductData.quantity,
                        // NOTE: no uom since not handled in combo configurator
                        linked_products: selectedComboItems.map(
                            (comboItem) => this._serializeComboItem(
                                comboItem, productTemplateId, comboProductData.quantity
                            )
                        ),
                        shouldRedirectToCart: options.goToCart,
                        ...additionalData,
                    }));
                },
                discard: () => resolve(0),
            });
        });
    }

    /**
     * Opens the product configurator dialog.
     *
     * The configurator data is preloaded by {@link add} (through
     * `/website_sale/product_configurator/get_values`) to save the dialog an RPC.
     *
     * @param {Number} productTemplateId - The product template id, as a `product.template` id.
     * @param {Object[]} products - The main product's information, as returned by
     *      `_get_product_information` (one element).
     * @param {Object[]} optionalProducts - The optional products' information, as returned by
     *      `_get_product_information`, with their `parent_product_tmpl_id`.
     * @param {Number} currencyId - The currency of the prices, as a `res.currency` id.
     * @param {CustomAttributeValues[]} productCustomAttributeValues - An array of objects
     *      representing custom attribute values for the product.
     * @param {Object} [options] - Define how to add products to the cart.
     * @param {Boolean} [options.isBuyNow] - Whether the product should be added immediately,
     *      bypassing optional configurations.
     * @param {Boolean} [options.isMainProductConfigurable] - Whether the product should be
     *      configurable.
     * @param {Object} [additionalData] - Additional data sent to the controllers.
     *
     * @returns {Number} - The product's quantity added to the cart.
     */
    async _openProductConfigurator(
        productTemplateId,
        products,
        optionalProducts,
        currencyId,
        productCustomAttributeValues,
        options,
        additionalData
    ) {
        return await new Promise((resolve) => {
            this.dialog.add(ProductConfiguratorDialog, {
                productTemplateId: productTemplateId,
                products: products,
                optionalProducts: optionalProducts,
                currencyId: currencyId,
                customPtavs: productCustomAttributeValues.map(customPtav => ({
                    id: customPtav.custom_product_template_attribute_value_id,
                    value: customPtav.custom_value,
                })),
                soDate: serializeDateTime(DateTime.now()),
                edit: false,
                isFrontend: true,
                selectedComboItems: [],  // optional products for combo aren't supported on ecommerce for now.
                options,
                ...additionalData,
                save: async (mainProduct, optionalProducts, options) => {
                    const product = this._serializeProduct(mainProduct);
                    resolve(this._makeRequest({
                        productTemplateId: product.product_template_id,
                        productId: product.product_id,
                        quantity: product.quantity,
                        uom_id: product.uom_id,
                        productCustomAttributeValues: product.product_custom_attribute_values,
                        noVariantAttributeValues: product.no_variant_attribute_value_ids,
                        linked_products: optionalProducts.flatMap(p => this._serializeProduct(p)),
                        shouldRedirectToCart: options.goToCart,
                        ...additionalData,
                    }));
                },
                discard: () => resolve(0),
            });
        });
    }

    /**
     * Serialize a product into a format understandable by the server.
     *
     * @param {Object} product - The product to serialize.
     *
     * @returns {Object|Object[]} - The serialized product, or an array containing the serialized
     *     product followed by its serialized combo items if the product is an optional combo.
     */
    _serializeProduct(product) {
        let serializedProduct = {
            product_id: product.id,
            product_template_id: product.product_tmpl_id,
            parent_product_template_id: product.parent_product_tmpl_id,
            quantity: product.quantity,
            uom_id: product.uom.id,
        }

        if (!product.attribute_lines) {
            return serializedProduct;
        }

        const { customPtavs, noVariantPtavIds } = getConfiguredPtavs(product);
        serializedProduct.product_custom_attribute_values = customPtavs.map(customPtav => ({
            custom_product_template_attribute_value_id: customPtav.id,
            custom_value: customPtav.value ?? '',
        }));
        serializedProduct.no_variant_attribute_value_ids = noVariantPtavIds;

        // If this optional product is a combo, also serialize its selected combo items so
        // the server can create the corresponding cart lines linked to this product's line.
        if (product.selectedComboItems?.length) {
            return [
                serializedProduct,
                ...product.selectedComboItems.map(
                    comboItem => this._serializeComboItem(
                        comboItem, product.product_tmpl_id, product.quantity
                    )
                ),
            ];
        }

        return serializedProduct;
    }

    /**
     * Serialize a combo item into a format understandable by the server.
     *
     * @param {ProductComboItem} comboItem - The combo item to serialize.
     * @param {Number} parentProductTemplateId - The parent's product template id, as a
     *      `product.template` id.
     * @param {Number} quantity - The quantity to add to the cart.
     *
     * @returns {Object} - The serialized combo item.
     */
    _serializeComboItem(comboItem, parentProductTemplateId, quantity) {
        return {
            product_template_id: comboItem.product.product_tmpl_id,
            parent_product_template_id: parentProductTemplateId,
            quantity: quantity,
            ...serializeComboItem(comboItem),
        };
    }

    //--------------------------------------------------------------------------
    // Helpers
    //--------------------------------------------------------------------------

    /**
     * Make a request to the server to add the product to the cart.
     *
     * @param {Object} data - Data containing product(s) to add to the cart and options for adding
     *      them.
     * @param {Number} data.productTemplateId - The product template's id, as a
     *      `product.template` id.
     * @param {Number} data.productId - The product's id, as a `product.product` id.
     * @param {Number} data.uomId - The uom's id, as a `uom.uom` id.
     * @param {Number} data.quantity - The quantity of the product to add to the cart.
     * @param {CustomAttributeValues[]} [data.productCustomAttributeValues=[]] - An
     *      array of objects representing custom attribute values for the product.
     * @param {Number[]} [data.noVariantAttributeValues=[]] - The selected non-stored
     *      attribute(s), as a list of `product.template.attribute.value` ids.
     * @param {Boolean} [data.shouldRedirectToCart=false] - Whether to redirect the
     *      customer to the cart. Defaults to false.
     * @param {Boolean} [data.showNotification=true] - Whether to show the cart notifications.
     * @param {Boolean} [data.skipOrderAlert=false] - Whether to not store the warning on the
     *      order when it can't be attached to a line.
     * @param {Boolean} [data.renderShorterCartSummary=false] - Whether to render the shorter cart
     *      summary.
     * @param {...*} [data.rest] - Locally unused data sent to the controllers.
     *
     * @returns {Number} - The product's quantity in the cart.
     */
    async _makeRequest({
        productTemplateId,
        productId,
        quantity,
        uomId=undefined,
        productCustomAttributeValues=[],
        noVariantAttributeValues=[],
        shouldRedirectToCart=false,
        showNotification=true,
        skipOrderAlert=false,
        renderShorterCartSummary=false,
        ...rest
    }) {
        const data = await this.rpc('/shop/cart/add', {
            product_template_id: productTemplateId,
            product_id: productId,
            quantity: quantity,
            uom_id: uomId,
            product_custom_attribute_values: productCustomAttributeValues,
            no_variant_attribute_value_ids: noVariantAttributeValues,
            skip_order_alert: skipOrderAlert,
            render_shorter_cart_summary: renderShorterCartSummary,
            ...rest
        }).catch(error => {
            this._showCartNotification({
                type: 'warning',
                data: { warning_message: error.data.message },
            });
            return null;
        });
        if (!data) {
            return 0;
        }
        if (data.quantity && data.tracking_info?.length) {
            wSaleUtils.dispatchTrackingEvent("add_to_cart_event", {
                currency: data.currency,
                items: data.tracking_info,
            });
        }
        if (shouldRedirectToCart) {
            redirect('/shop/cart');
            return data.quantity;
        }
        if (data.cart_quantity && (
            data.cart_quantity !== browser.sessionStorage.getItem('website_sale_cart_quantity')
        )) {
            this._updateCartIcon(data.cart_quantity);
        }
        if (showNotification) {
            for (const notification of data.notifications) {
                this._showCartNotification(notification);
            }
        }
        if (data["website_sale.shorter_cart_summary"]) {
            data["website_sale.shorter_cart_summary"] = markup(
                data["website_sale.shorter_cart_summary"]
            );
            this._renderCartSummary(data);
        }
        this.bus.trigger("cart_amount_changed", [data.amount, data.minor_amount]);
        return data.quantity;
    }

    /**
     * Update the quantity on the cart icon in the navbar.
     *
     * @param {Number} cartQuantity - The number of items currently in the cart.
     *
     * @returns {void}
     */
    _updateCartIcon(cartQuantity) {
        browser.sessionStorage.setItem('website_sale_cart_quantity', cartQuantity);
        // Mobile and Desktop elements have to be updated.
        const cartQuantityElements = document.querySelectorAll('.my_cart_quantity');
        for (const cartQuantityElement of cartQuantityElements) {
            if (cartQuantity === 0) {
                cartQuantityElement.classList.add('d-none');
            } else {
                const cartIconElement = document.querySelector('li.o_wsale_my_cart');
                cartIconElement.classList.remove('d-none');
                cartQuantityElement.classList.remove('d-none');
                cartQuantityElement.classList.add('o_mycart_zoom_animation');
                setTimeout(() => {
                    cartQuantityElement.textContent = cartQuantity;
                    cartQuantityElement.classList.remove('o_mycart_zoom_animation');
                }, 300);
            }
        }
    }

    /**
     * Show the notification about the cart.
     *
     * @param {Object} notification
     *
     * @returns {void}
     */
    _showCartNotification(notification) {
        this.notifications.add(notification);
        setTimeout( () => this.notifications.delete(notification), AUTOCLOSE_NOTIFICATION_DELAY );
    }

    /**
     * Render the cart summary. This could be useful in cases like quick reorder where we add the
     * product to the empty cart from cart page itself.
     *
     * @param {Object} data - The `/shop/cart/add` response, containing the rendered cart summary.
     *
     * @returns {void}
     */
    _renderCartSummary(data) {
        const cartSummarySelector = ".o_wsale_shorter_cart_summary";
        this.interactions.stopInteractions(document.querySelector(cartSummarySelector));
        wSaleUtils.updateCartSummary(data);
        // Start the interactions of the whole summary, totals, express checkout etc.
        this.interactions.startInteractions(document.querySelector(cartSummarySelector));
    }

    /**
     * Fetch the cart data from the server and store it in the {@link state}, unless it is already
     * loaded and the reload is not forced.
     *
     * Must only be called through {@link loadCart}, which serializes the calls.
     *
     * @param {Boolean} force - Whether to fetch the data even if it was already loaded.
     * @param {Boolean} fromConfirmationPage - Whether to load the last confirmed order instead of
     *      the current cart.
     * @param {Boolean} withHistory - Whether to also load the order history of the customer.
     *
     * @returns {Promise<void>}
     */
    async _loadCartData(force, fromConfirmationPage, withHistory) {
        if (force || !this.cartLoaded) {
            const data = await this.rpc("/shop/cart/data", {
                from_confirmation_page: fromConfirmationPage,
                with_history: withHistory,
            });
            this._setCartState(data);
            this.cartLoaded = true;
        }
    }

    /**
     * Merge the cart data into the reactive {@link state}, triggering the re-render of the
     * components reading it.
     *
     * Override this method to store additional cart data in the state.
     *
     * @param {Object} data - The `/shop/cart/data` response.
     * @param {Object} [data.lines] - The cart lines and their related data.
     * @param {Object} [data.totals] - The order amounts.
     * @param {Object} [data.history] - The order history, grouped by date.
     * @param {Number|null} data.currency_id - The order's currency id, as a `res.currency` id.
     * @param {Boolean} data.is_quantity_view_active - Whether the quantity selector is enabled.
     * @param {Boolean} data.is_wishlist_view_active - Whether the wishlist is enabled.
     * @param {Boolean} data.show_product_reference_price - Whether the product reference price
     *      is shown.
     *
     * @returns {void}
     */
    _setCartState(data) {
        this.state.lines = data.lines;
        this.state.totals = data.totals;
        this.state.history = data.history;
        this.state.currency_id = data.currency_id;
        this.state.is_quantity_view_active = data.is_quantity_view_active;
        this.state.is_wishlist_view_active = data.is_wishlist_view_active;
        this.state.show_product_reference_price = data.show_product_reference_price;
    }
}

export const cartService = {
    dependencies: CartService.dependencies,
    async: ["add", "update", "loadCart"],
    start(env, dependencies) {
        return new CartService(env, dependencies);
    },
}

registry.category('services').add('cart', cartService);
