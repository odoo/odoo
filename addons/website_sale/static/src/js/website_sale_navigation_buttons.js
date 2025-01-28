import { rpc, RPCError } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { Interaction } from '@web/public/interaction';
import wSaleUtils from '@website_sale/js/website_sale_utils';


const PATHS_TO_CHECK = [
    '/shop/checkout',
    '/shop/confirm_order',
];
const END_PATHS = [
    '/shop/confirm_order',
];


export class WebsiteSaleNavigationButton extends Interaction {
    static selector = '#navigation_buttons';
    dynamicContent = PATHS_TO_CHECK.reduce(
        (acc, path) => {
            acc[`a[name='website_sale_main_button'][href*='${path}']`] = {
                't-on-click': this._checkCart
            };
            return acc;
        },
        {},
    );

    /**
     * Calls /shop/check_cart before continuing the flow
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _checkCart(ev) {
        // href could contain the path but in the parameters
        if (!PATHS_TO_CHECK.includes(ev.target.pathname)) {
            return;
        }
        ev.preventDefault(); // manual override
        rpc('/shop/check_cart', { ready_to_be_paid: END_PATHS.includes(ev.target.pathname) })
            .then(() => window.location.href = ev.target.href)
            .catch(error => {
                if (error instanceof RPCError) {
                    wSaleUtils.showWarning(error.data.message);
                } else {
                    return Promise.reject(error);
                }
            });
    }
}

registry
    .category('public.interactions')
    .add('website_sale.WebsiteSaleNavigationButton', WebsiteSaleNavigationButton);
