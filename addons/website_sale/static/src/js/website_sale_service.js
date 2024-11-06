import {
    ComboConfiguratorDialog
} from '@sale/js/combo_configurator_dialog/combo_configurator_dialog';
import { ProductCombo } from '@sale/js/models/product_combo';
import {
    ProductConfiguratorDialog
} from '@sale/js/product_configurator_dialog/product_configurator_dialog';
import { serializeComboItem } from '@sale/js/sale_utils';
import { browser } from '@web/core/browser/browser';
import { serializeDateTime } from '@web/core/l10n/dates';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { session } from '@web/session';

const { DateTime } = luxon;

/**
 * Manages product addition via the {@link addToCart} function.
 *
 * This function handles the process of adding products to the cart, including:
 * - Opening configurators if needed;
 * - Updating the cart with the selected products;
 * - Updating the cart count in the navbar;
 * - Notifying the customer of successful additions;
 * - Track the added products.
 *
 * Override this class to implement additional checks or
 * provide relevant information when adding a product to the cart.
 */
export class WebsiteSaleService {
    static dependencies = ['cartNotificationService', 'dialog'];

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
        this.cartNotificationService = services.cartNotificationService;
        this.dialog = services.dialog;
        this.rpc = rpc;  // To be overridable in tests.

        // Only expose `addToCart` in the service registry.
        let self = this;
        return {
            addToCart: function() {
                return self.addToCart(...arguments);
            }
        }
    }

    //--------------------------------------------------------------------------
    // Public methods
    //--------------------------------------------------------------------------

    /**
     * Asynchronously adds a product to the shopping cart.
     *
     * @async
     * @param {Object} product - The product details to add to the cart.
     * @param {Number} product.productTemplateId - The product template's id, as a
     *      `product.template` id.
     * @param {Number} [product.productId=undefined] - The product's id, as a `product.product` id.
     *      If not provided, selects the first available product or creates one if any attribute is
     *      dynamic.
     * @param {Number} [product.quantity=1] - The quantity of the product to add to the cart.
     *      Defaults to 1.
     * @param {Number[]} [product.ptavs=[]] - The selected stored attribute(s), as a list of
     *      `product.template.attribute.value` ids.
     * @param {{id: Number, value: String}[]} [product.productCustomAttributeValues=[]] - An
     *      array of objects representing custom attribute values for the product. Each object
     *      contains:
     *      - `custom_product_template_attribute_value_id`: The custom attribute's id.
     *      - `custom_value`: The custom attribute's value.
     * @param {Number[]} [product.noVariantAttributeValues=[]] - The selected non-stored
     *      attribute(s), as a list of `product.template.attribute.value` ids.
     * @param {Boolean} [product.isCombo=false] - Whether the product is part of a combo template.
     *      Defaults to false.
     * @param {...*} [product.rest] - Locally unused data sent to the controllers.
     * @param {Object} [options] - Define how to add products to the cart.
     * @param {Boolean} [options.isBuyNow=false] - Whether the product should be added immediately,
     *      bypassing optional configurations. Defaults to false.
     * @param {Boolean} [options.redirectToCart=true] - When `isBuyNow` is `true`, whether to
     *      redirect the customer to the cart. Defaults to true.
     * @param {Boolean} [options.isConfigured=false] - Whether the product is already configured.
     *      Defaults to false.
     *
     * @returns {Number} - The product's quantity added to the cart.
     */
    async addToCart({
            productTemplateId,
            productId = undefined,
            quantity = 1,
            ptavs = [],
            productCustomAttributeValues = [],
            noVariantAttributeValues = [],
            isCombo = false,
            ...rest
        },
        {
            isBuyNow=false,
            redirectToCart=true,
            isConfigured=false,
        } = {},
    ) {
        if (!productId && ptavs.length) {
            productId = await this.rpc('/sale/create_product_variant', {
                product_template_id: productTemplateId,
                product_template_attribute_value_ids: JSON.stringify(ptavs),
            })
        }

        if(isCombo) {
            const { combos, ...remainingData } = await this.rpc(
                '/website_sale/combo_configurator/get_data',
                {
                    product_tmpl_id: productTemplateId,
                    quantity: quantity,
                    date: serializeDateTime(DateTime.now()),
                }
            );
            return this._openComboConfigurator(
                productTemplateId,
                productId,
                combos.map(combo => new ProductCombo(combo)),
                remainingData,
                rest
            );
        }

        if (isBuyNow) {
            return this._addToCart({
                productTemplateId,
                productId,
                quantity,
                productCustomAttributeValues,
                noVariantAttributeValues,
                redirectToCart: isBuyNow && redirectToCart,
                ...rest
            });
        }

        const shouldShowProductConfigurator = await this.rpc(
            '/website_sale/should_show_product_configurator',
            {
                product_template_id: productTemplateId,
                ptav_ids: ptavs,
                is_product_configured: isConfigured,
            }
        );
        if (shouldShowProductConfigurator) {
            return this._openProductConfigurator(
                productTemplateId,
                quantity,
                ptavs.concat(noVariantAttributeValues),
                productCustomAttributeValues,
                isConfigured,
                rest
            );
        }

        return this._addToCart({
            productTemplateId,
            productId,
            quantity,
            productCustomAttributeValues,
            noVariantAttributeValues,
            redirectToCart: isBuyNow && redirectToCart,
            ...rest
        });
    }

    //--------------------------------------------------------------------------
    // Configurators
    //--------------------------------------------------------------------------

    /**
     * Opens the combo configurator dialog.
     *
     * @private
     * @param {Number} productId - The product's id, as a `product.product` id.
     * @param {ProductCombo[]} combos - The combos of the product.
     * @param {Object} remainingData - Other data needed to open the combo configurator.
     * @param {String} remainingData.category_name - The category's name of the combo.
     * @param {Number} remainingData.currency_id - The currency's id, as a `res.currency` id.
     * @param {String} remainingData.currency_name - The name of the currency.
     * @param {String} remainingData.display_name - The name of the combo.
     * @param {Number} remainingData.price - The price of the combo.
     * @param {Number} remainingData.product_tmpl_id - The product template's id, as a
     *      `product.template` id.
     * @param {Number} remainingData.quantity - The quantity of the combo.
     *
     * @returns {Number} - The product's quantity added to the cart.
     */
    async _openComboConfigurator(productTemplateId, productId, combos, remainingData, rest) {
        return await new Promise((resolve) => {
            this.dialog.add(ComboConfiguratorDialog, {
                combos: combos,
                ...remainingData,
                date: serializeDateTime(DateTime.now()),
                edit: false,
                isFrontend: true,
                ...rest,
                save: async (comboProductData, selectedComboItems, options) => {
                    resolve(this._addToCart({
                        productTemplateId,
                        productId,
                        quantity: comboProductData.quantity,
                        is_combo: true,
                        linked_products: selectedComboItems.map(
                            (comboItem) => this._serializeComboItem(
                                comboItem, productTemplateId, comboProductData.quantity
                            )
                        ),
                        redirectToCart: options.goToCart,
                        ...rest,
                    }));
                },
                discard: () => resolve(0),
            });
        });
    }

    /**
     * Opens the product configurator dialog.
     *
     * @private
     * @param {Number} productTemplateId - The product template id, as a `product.template` id.
     * @param {Number} quantity - The quantity to add to the cart.
     * @param {Number[]} combination - The combination of the product, as a list of
     *      `product.template.attribute.value` ids.
     * @param {{id: Number, value: String}[]} [productCustomAttributeValues=[]] - An array of
     *      objects representing custom attribute values for the product. Each object contains:
     *      - `custom_product_template_attribute_value_id`: The custom attribute's id.
     *      - `custom_value`: The custom attribute's value.
     *
     * @returns {Number} - The product's quantity added to the cart.
     */
    async _openProductConfigurator(
        productTemplateId,
        quantity,
        combination,
        productCustomAttributeValues,
        isConfigured,
        rest
    ) {
        return await new Promise((resolve) => {
            this.dialog.add(ProductConfiguratorDialog, {
                productTemplateId: productTemplateId,
                ptavIds: combination,
                customPtavs: productCustomAttributeValues.map(customPtav => ({
                    id: customPtav.custom_product_template_attribute_value_id,
                    value: customPtav.custom_value,
                })),
                quantity: quantity,
                soDate: serializeDateTime(DateTime.now()),
                edit: false,
                isFrontend: true,
                options: { isMainProductConfigurable: !isConfigured },
                ...rest,
                save: async (mainProduct, optionalProducts, options) => {
                    const product = this._serializeProduct(mainProduct);
                    resolve(this._addToCart({
                        productTemplateId: product.product_template_id,
                        productId: product.product_id,
                        quantity: product.quantity,
                        productCustomAttributeValues: product.product_custom_attribute_values,
                        noVariantAttributeValues: product.no_variant_attribute_value_ids,
                        linked_products: optionalProducts.map(this._serializeProduct),
                        redirectToCart: options.goToCart,
                        ...rest,
                    }));
                },
                discard: () => resolve(0),
            });
        });
    }

    /**
     * Serialize a product into a format understandable by the server.
     *
     * @private
     * @param {Object} product - The product to serialize.
     *
     * @returns {Object} - The serialized product.
     */
    _serializeProduct(product) {
        let serializedProduct = {
            product_id: product.id,
            product_template_id: product.product_tmpl_id,
            parent_product_template_id: product.parent_product_tmpl_id,
            quantity: product.quantity,
        }

        if (!product.attribute_lines) {
            return serializedProduct;
        }

        // Custom attributes.
        serializedProduct.product_custom_attribute_values = [];
        for (const ptal of product.attribute_lines) {
            const selectedPtavIds = new Set(ptal.selected_attribute_value_ids);
            const selectedCustomPtav = ptal.attribute_values.find(
                ptav => ptav.is_custom && selectedPtavIds.has(ptav.id)
            );
            if (selectedCustomPtav) {
                serializedProduct.product_custom_attribute_values.push({
                    custom_product_template_attribute_value_id: selectedCustomPtav.id,
                    custom_value: ptal.customValue ?? '',
                });
            }
        }

        // No variant attributes.
        serializedProduct.no_variant_attribute_value_ids = product.attribute_lines
            .filter(ptal => ptal.create_variant === 'no_variant')
            .flatMap(ptal => ptal.selected_attribute_value_ids);

        return serializedProduct;
    }

    /**
     * Serialize a combo item into a format understandable by the server.
     *
     * @private
     * @param {ProductComboItem} comboItem - The combo item to serialize.
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
     * Asynchronously adds a product to the shopping cart.
     *
     * @async
     * @private
     * @param {Object} product - The product details to add to the cart.
     * @param {Number} product.productTemplateId - The product template's id, as a
     *      `product.template` id.
     * @param {Number} product.productId - The product's id, as a `product.product` id.
     * @param {Number} product.quantity - The quantity of the product to add to the cart.
     * @param {{id: Number, value: String}[]} [product.productCustomAttributeValues=[]] - An
     *      array of objects representing custom attribute values for the product. Each object
     *      contains:
     *      - `custom_product_template_attribute_value_id`: The custom attribute's id.
     *      - `custom_value`: The custom attribute's value.
     * @param {Number[]} [product.noVariantAttributeValues=[]] - The selected non-stored
     *      attribute(s), as a list of `product.template.attribute.value` ids.
     * @param {Boolean} [isBuyNow=false] - Whether the product should be added immediately,
     *      bypassing optional configurations. Defaults to false.
     * @param {...*} [product.rest] - Locally unused data sent to the controllers.
     *
     * @returns {Number} - The product's quantity added to the cart.
     */
    async _addToCart({
        productTemplateId,
        productId,
        quantity,
        productCustomAttributeValues=[],
        noVariantAttributeValues=[],
        redirectToCart=false,
        ...rest
    }) {
        const data = await this.rpc('/shop/cart/add', {
            product_template_id: productTemplateId,
            product_id: productId,
            quantity: quantity,
            product_custom_attribute_values: productCustomAttributeValues,
            no_variant_attribute_value_ids: noVariantAttributeValues,
            force_create: true,
            ...rest
        });
        // TODO VCR should not redirect if errors in data.
        if (redirectToCart || session.add_to_cart_action === 'go_to_cart') {
            window.location = '/shop/cart';
            return data.quantity;
        }
        if (data.cart_quantity && (
            data.cart_quantity !== browser.sessionStorage.getItem('website_sale_cart_quantity')
        )) {
            this._updateCartIcon(data.cart_quantity);
        };
        this._showCartNotification(data.notification_info);
        this._trackProducts(data.tracking_info);
        return data.quantity;
    }

    /**
     * Update the quantity on the cart icon in the navbar.
     *
     * @private
     * @param {Number} cartQuantity - The number of items currently in the cart.
     *
     * @returns {void}
     */
    _updateCartIcon(cartQuantity) {
        browser.sessionStorage.setItem('website_sale_cart_quantity', cartQuantity);
        // Mobile and Desktop elements have to be updated.
        const cartQuantityElements = document.querySelectorAll('.my_cart_quantity');
        for(const cartQuantityElement of cartQuantityElements) {
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
     * @private
     * @param {Object} props
     * @param {Object} options
     *
     * @returns {void}
     */
    _showCartNotification(props, options = {}) {
        if (props.lines) {
            this.cartNotificationService.add(_t('Item(s) added to your cart'), {
                lines: props.lines,
                currency_id: props.currency_id,
                ...options,
            });
        }
        if (props.warning) {
            this.cartNotificationService.add(_t('Warning'), {
                warning: props.warning,
                ...options,
            });
        }
    }

    /**
     * Track the products added to the cart.
     *
     * @private
     * @param {Object[]} trackingInfo - A list of product tracking information.
     *
     * @returns {void}
     */
    _trackProducts(trackingInfo) {
        document.querySelector('.oe_website_sale').dispatchEvent(
            new CustomEvent('add_to_cart_event', {'detail': trackingInfo})
        );
    }
}

export const websiteSaleService = {
    dependencies: WebsiteSaleService.dependencies,
    async: ['addToCart'],
    start(env, dependencies) {
        return new WebsiteSaleService(env, dependencies);
    },
}

registry.category('services').add('websiteSale', websiteSaleService);
