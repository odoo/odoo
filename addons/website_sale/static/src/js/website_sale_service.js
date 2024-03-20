/** @odoo-module **/

import { reactive } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";

export const websiteSaleService = {
    dependencies: ['cartNotificationService'],

    async start(env, { cartNotificationService }) {
        const context = reactive({
            nbItemsInCart: sessionStorage.getItem('website_sale_cart_quantity')
        });
        const options = {
            addToCartAction: session.add_to_cart_action,
        }

        async function addToCart(params, isBuyNow=false) {
            if (isBuyNow) {
                params.express = true;
            } else if (options.addToCartAction === 'stay') {
                const data = await rpc('/shop/cart/update_json', {
                    ...params,
                    display: false,
                    force_create: true,
                });
                if (data.cart_quantity && (data.cart_quantity !== parseInt($('.my_cart_quantity').text()))) {
                    updateCartNavBar(data);
                };
                _showCartNotification(data.notification_info);
                return data;
            }
            // return wUtils.sendRequest('/shop/cart/update', params);
        }

        /*
         * Will return a promise:
         *
         * - If the product already exists, immediately resolves it with the product_id
         * - If the product does not exist yet ("dynamic" variant creation), this method will
         *   create the product first and then resolve the promise with the created product's id
         *
         * @param {integer} productId the product id
         * @param {integer} productTemplateId the corresponding product template id
         * @returns {Promise} the promise that will be resolved with a {integer} productId
         */
        function selectOrCreateProduct(productId, productTemplateId, ptavs) {
            productId = parseInt(productId);
            productTemplateId = parseInt(productTemplateId);
            var productReady = Promise.resolve();
            if (productId) {
                productReady = Promise.resolve(productId);
            } else {
                productReady = rpc('/sale/create_product_variant', {
                    product_template_id: productTemplateId,
                    product_template_attribute_value_ids: ptavs,
                });
            }

            return productReady;
        }

        /**
         * Updates both navbar cart
         * @param {Object} data
         */
        function updateCartNavBar(data) {
            sessionStorage.setItem('website_sale_cart_quantity', data.cart_quantity);
            $(".my_cart_quantity")
                .parents('li.o_wsale_my_cart').removeClass('d-none').end()
                .toggleClass('d-none', data.cart_quantity === 0)
                .addClass('o_mycart_zoom_animation').delay(300)
                .queue(function () {
                    $(this)
                        .toggleClass('fa fa-warning', !data.cart_quantity)
                        .attr('title', data.warning)
                        .text(data.cart_quantity || '')
                        .removeClass('o_mycart_zoom_animation')
                        .dequeue();
                });

            $(".js_cart_lines").first().before(data['website_sale.cart_lines']).end().remove();
            $("#cart_total").replaceWith(data['website_sale.total']);
            if (data.cart_ready) {
                document.querySelector("a[name='website_sale_main_button']")?.classList.remove('disabled');
            } else {
                document.querySelector("a[name='website_sale_main_button']")?.classList.add('disabled');
            }
        }

        // TODO VCR add tracking
        // TODO VCR handle navbar from here

        function _showCartNotification(props, options = {}) {
            // Show the notification about the cart
            if (props.lines) {
                cartNotificationService.add(_t('Item(s) added to your cart'), {
                    lines: props.lines,
                    currency_id: props.currency_id,
                    ...options,
                });
            }
            if (props.warning) {
                cartNotificationService.add(_t('Warning'), {
                    warning: props.warning,
                    ...options,
                });
            }
        }

        return { addToCart };
    },
}

registry.category('services').add('website_sale', websiteSaleService);
