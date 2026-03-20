import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { SIZES, utils as uiUtils } from '@web/core/ui/ui_service';

export class ScrollableTable extends Interaction {
    static selector = '.o_wsale_scrollable_table';
    dynamicContent = {
        _root: {
            't-on-scroll': this.throttled(this.onScroll, 100),
        },
        _window: {
            't-on-resize': this.debounced(this.updateMobileBadgeVisibility, 250),
        },
    };

    setup() {
        // This class exists when there are more than 4 items in the cart.
        this.badgeDesktopEl = this.el.querySelector('.o_wsale_scrollable_table_badge_desktop');
        // On mobile the badge is in .offcanvas-footer, it's not a child of
        // .o_wsale_scrollable_table (the scrollable element)
        const offCanvasEl = this.el.closest('.offcanvas');
        this.badgeMobileEl = offCanvasEl?.querySelector('.o_wsale_scrollable_table_badge_mobile');
        this.updateMobileBadgeVisibility();
    }

    updateMobileBadgeVisibility() {
        this.isMobile = uiUtils.getSize() < SIZES.LG;
        const scrollAmount = this.el.scrollHeight - this.el.clientHeight;
        const minScrollAmount = 24; // half image height at 1:1 ratio
        if (this.badgeMobileEl && this.isMobile) {
            this.badgeMobileEl.classList.toggle('d-none', scrollAmount < minScrollAmount);
        }
    }

    onScroll() {
        const isScrolled = this.el.scrollTop > 0;
        const badgeEl = this.isMobile ? this.badgeMobileEl : this.badgeDesktopEl;
        if (badgeEl) {
            badgeEl.classList.toggle('o_scrollable_table_badge_hidden', isScrolled);
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale.scrollable_table', ScrollableTable);

registry
    .category('public.interactions.edit')
    .add('website_sale.scrollable_table', {
        Interaction: ScrollableTable,
    });
