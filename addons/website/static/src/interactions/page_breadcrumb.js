import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PageBreadcrumb extends Interaction {
    static selector = "div.o_page_breadcrumb";
    dynamicContent = {
        _window: {
            "t-on-resize": this.updatePageBreadcrumbOnResize,
        },
    };

    start() {
        const headerEl = document.querySelector("header#top");
        if (headerEl) {
            // Watch the header element so we can reposition the breadcrumb
            // whenever the header's height changes (e.g. on resize or style updates).
            this.headerObserver = new ResizeObserver(() => {
                this.updatePageBreadcrumbOnResize();
            });
            this.headerObserver.observe(headerEl);
        }
    }

    /**
     * Calculates the breadcrumb position so it stays aligned
     * directly below the header.
     */
    updatePageBreadcrumbOnResize() {
        const headerHeight = document
            .querySelector(".o_header_overlay header#top")
            ?.getBoundingClientRect().height;
        if (headerHeight) {
            this.el.style.top = `${headerHeight}px`;
        }
    }
}

registry.category("public.interactions").add("website.page_breadcrumb", PageBreadcrumb);

registry.category("public.interactions.edit").add("website.page_breadcrumb", {
    Interaction: PageBreadcrumb,
});
