import { BaseHeader } from "@website/interactions/header/base_header";
import { registry } from "@web/core/registry";

export class HeaderStandard extends BaseHeader {
    static selector = "header.o_header_standard:not(.o_header_sidebar)";

    setup() {
        super.setup();
        this.transitionPoint = 300;
        this.transitionPossible = false;
    }

    /**
     * Checks if the size of the header will decrease by adding the
     * 'o_header_is_scrolled' class. If so, we do not add this class if the
     * remaining scroll height is not enough to stay above 'this.transitionPoint'
     * after the transition, otherwise it causes the scroll position to move up
     * again below 'this.transitionPoint' and trigger an infinite loop.
     *
     * @todo header effects should be improved in the future to not ever change
     * the page scroll-height during their animation. The code would probably be
     * simpler but also prevent having weird scroll "jumps" during animations
     * (= depending on the logo height after/before scroll, a scroll step (one
     * mousewheel event for example) can be bigger than other ones).
     *
     * @returns {boolean}
     */
    canTransition() {
        const scrollEl = this.scrollingElement;
        const remainingScroll = (scrollEl.scrollHeight - scrollEl.clientHeight) - this.transitionPoint;
        const clonedHeader = this.el.cloneNode(true);
        scrollEl.append(clonedHeader);
        clonedHeader.classList.add('o_header_is_scrolled', 'o_header_affixed', 'o_header_no_transition');
        const endHeaderHeight = clonedHeader.offsetHeight;
        clonedHeader.remove();
        const requiredScroll = this.getHeaderHeight() - endHeaderHeight;
        return requiredScroll > 0 ? remainingScroll > requiredScroll : true;
    }

    onScroll() {
        const scroll = this.scrollingElement.scrollTop;

        const isScrolled = (scroll > this.transitionPoint);
        if (this.isScrolled !== isScrolled) {
            this.transitionPossible = this.canTransition() || !isScrolled;
            if (this.transitionPossible) {
                this.adaptToHeaderChangeLoop(1);
            }
        }

        const reachHeaderBottom = (scroll > this.getHeaderHeight() + this.topGap);
        const reachTransitionPoint = (scroll > this.transitionPoint + this.topGap) && this.transitionPossible;

        // TEMP : WAITING FOR odoo#189817
        if (this.atTop == reachHeaderBottom) {
            this.el.classList.add("o_transformed_not_affixed");
        }
        this.atTop = !reachHeaderBottom;

        reachTransitionPoint
            ? this.transformShow()
            : reachHeaderBottom
                ? this.transformHide()
                : this.transformShow()
        void this.el.offsetWidth; // Force a paint refresh

        // TEMP : WAITING FOR odoo#189817
        this.el.classList.remove("o_transformed_not_affixed");
        this.hideEl?.classList.toggle("hidden", reachHeaderBottom);

        this.toggleCSSAffixed(reachHeaderBottom);
        this.isScrolled = reachTransitionPoint;
    }
}

registry
    .category("public.interactions")
    .add("website.header_standard", HeaderStandard);

registry
    .category("public.interactions.edit")
    .add("website.header_standard", {
        Interaction: HeaderStandard,
    });
