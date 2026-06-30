import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class ProductStickyCol extends Interaction {
    static selector = '.o_wsale_product_sticky_col';
    dynamicContent = {
        _root: {
            't-att-style': () => ({
                'opacity': '1',
                'top': `${this.position || 16}px`,
            }),
        }
    };

    setup() {
        this.position = 16;
    }

    start() {
        this._adaptToHeaderChange();
        this.registerCleanup(
            this.services.website_menus.registerCallback(this._adaptToHeaderChange.bind(this))
        );
    }

    _adaptToHeaderChange() {
        let position = 16; // Add 1rem equivalent in px to provide a visual gap by default

        for (const el of document.querySelectorAll('.o_top_fixed_element')) {
            position += el.offsetHeight;
        }

        if (this.position !== position) {
            this.position = position;
            this.updateContent();
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale.product_sticky_col', ProductStickyCol);
