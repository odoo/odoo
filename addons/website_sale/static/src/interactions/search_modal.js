import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class SearchModal extends Interaction {
    static selector = "#o_wsale_search_modal, #o_wsale_product_search_modal";
    dynamicContent = {
        _root: {
            "t-on-shown.bs.modal": (ev) => ev.target.querySelector(".oe_search_box").focus(),
        },
    };
    destroy() {
        Modal.getInstance(this.el)?.hide();
    }
}

registry
    .category('public.interactions')
    .add('website_sale.search_modal', SearchModal);
