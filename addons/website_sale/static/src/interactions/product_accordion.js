import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class ProductAccordion extends Interaction {
    static selector = '#product_accordion';

    setup() {
        this._updateAccordionActiveItem();
    }

    /**
     * Open the already opened accordion item, or the first one by default.
     */
    _updateAccordionActiveItem() {
        const accordionItemEl =
            this.el.querySelector('.accordion-collapse.show')?.closest('.accordion-item')
            || this.el.querySelector('.accordion-item');
        const accordionItemButtonEl = accordionItemEl?.querySelector('.accordion-button');
        if (!accordionItemButtonEl) return;

        accordionItemButtonEl.classList.remove('collapsed');
        accordionItemButtonEl.setAttribute('aria-expanded', 'true');
        accordionItemEl.querySelector('.accordion-collapse').classList.add('show');
        this.el.classList.remove('o_accordion_not_initialized');
    }
}

registry
    .category('public.interactions')
    .add('website_sale.product_accordion', ProductAccordion);
