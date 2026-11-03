import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { getScrollingElement, getScrollingTarget } from '@web/core/utils/scrolling';

/**
 * De zwevende knop "Tijd om te feesten" onderaan het scherm.
 *
 * Bovenaan de pagina staat dezelfde oproep al in de header, dus daar zou de
 * knop dubbel zijn. Hij schuift pas in beeld zodra de bezoeker voorbij het
 * eerste scherm gescrold is, zoals op de site van B&B.
 *
 * Welk element scrollt verschilt in Odoo (het document, of #wrapwrap in
 * sommige lay-outs). `getScrollingElement` lost dat op, zodat we niet zelf
 * moeten raden.
 */
export class BypFloatingCta extends Interaction {
    static selector = '.o_byp_floating';

    setup() {
        this.scrollingElement = getScrollingElement(this.el.ownerDocument);
    }

    start() {
        // addListener mag pas vanaf start(); in setup() weigert Odoo het.
        this.addListener(getScrollingTarget(this.scrollingElement), 'scroll', this.update, { passive: true });
        this.update();
    }

    update() {
        const threshold = window.innerHeight * 0.6;
        this.el.classList.toggle('o_byp_visible', this.scrollingElement.scrollTop > threshold);
    }
}

registry.category('public.interactions').add('byp_website.floating_cta', BypFloatingCta);
