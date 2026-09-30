import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class ProductAccordion extends Interaction {
    static selector = '#product_accordion';

    setup() {
        this._updateAccordionActiveItem();
    }

    /**
     * Open the first accordion item by default.
     */
    _updateAccordionActiveItem() {
        const firstAccordionItemEl = this.el.querySelector('.accordion-item');
        if (!firstAccordionItemEl) return;

        const firstAccordionItemButtonEl = firstAccordionItemEl.querySelector('.accordion-button');
        firstAccordionItemButtonEl.classList.remove('collapsed');
        firstAccordionItemButtonEl.setAttribute('aria-expanded', 'true');
        firstAccordionItemEl.querySelector('.accordion-collapse').classList.add('show');
        this.el.classList.remove('o_accordion_not_initialized');
    }
}

registry
    .category('public.interactions')
    .add('website_sale.product_accordion', ProductAccordion);
