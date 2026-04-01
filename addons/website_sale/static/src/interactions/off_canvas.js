import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class OffCanvas extends Interaction {
    static selector = '#o_wsale_offcanvas';
    dynamicContent = {
        _root: {
            't-on-show.bs.offcanvas': this.toggleFilters,
            't-on-hidden.bs.offcanvas': this.toggleFilters,
        },
    };

    /**
     * Unfold active filters, fold inactive ones
     *
     * @param {Event} ev
     */
    toggleFilters(ev) {
        for (const btn of this.el.querySelectorAll('button[data-status]')) {
            if (
                btn.classList.contains('collapsed') && btn.dataset.status === 'active'
                || !btn.classList.contains('collapsed') && btn.dataset.status === 'inactive'
            ) {
                btn.click();
            }
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale.off_canvas', OffCanvas);
