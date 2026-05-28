import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import wSaleUtils from '@website_sale/js/website_sale_utils';

export class PriceRange extends Interaction {
    static selector = '#o_wsale_price_range_option';
    dynamicContent = {
        'input[type="range"]': { 't-on-newRangeValue': this.onPriceRangeSelected },
    };

    /**
     * @param {Event} ev
     */
    async onPriceRangeSelected(ev) {
        const range = ev.currentTarget;
        const url = new URL(range.dataset.url, window.location.origin);
        const searchParams = url.searchParams;
        if (parseFloat(range.min) !== range.valueLow) {
            searchParams.set("min_price", range.valueLow);
        }
        if (parseFloat(range.max) !== range.valueHigh) {
            searchParams.set("max_price", range.valueHigh);
        }
        await wSaleUtils.updateShopContent(this, {
            url,
            searchParams,
        });
    }
}

registry
    .category('public.interactions')
    .add('website_sale.price_range', PriceRange);
