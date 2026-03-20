import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PageBreadcrumb extends Interaction {
    static selector = ".o_page_breadcrumb";

    start() {
        this.headerEl = document.querySelector("#top");
        // Watch the header element so we can reposition the breadcrumb whenever
        // the header's height changes (e.g. on resize or style updates).
        const updatePageBreadcrumbOnResize = this.protectSyncAfterAsync(
            this.updatePageBreadcrumbOnResize.bind(this)
        );
        this.headerObserver = new ResizeObserver(updatePageBreadcrumbOnResize);
        this.headerObserver.observe(this.headerEl);
    }

    destroy() {
        this.headerObserver.disconnect();
    }

    /**
     * Calculates the breadcrumb position so it stays aligned directly below the
     * header.
     */
    updatePageBreadcrumbOnResize() {
        const headerHeight = this.headerEl.getBoundingClientRect().height;
        this.el.style.top = `${headerHeight}px`;
    }
}

registry.category("public.interactions").add("website.page_breadcrumb", PageBreadcrumb);

registry.category("public.interactions.edit").add("website.page_breadcrumb", {
    Interaction: PageBreadcrumb,
});
