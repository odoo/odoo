import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class SearchModal extends Interaction {
    static selector = '#o_wsale_search_modal';

    start() {
        this.el.addEventListener('shown.bs.modal', (ev) =>
            ev.target.querySelector('.oe_search_box').focus()
        );
    }
}

registry
    .category('public.interactions')
    .add('website_sale.search_modal', SearchModal);
