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
        if (this.headerEl) {
            this.headerObserver = new ResizeObserver(updatePageBreadcrumbOnResize);
            this.headerObserver.observe(this.headerEl);
            this.registerCleanup(() => this.headerObserver.disconnect());
        }
    }

    /**
     * Exposes the header height as a CSS variable, used to keep the breadcrumb
     * below the header when the header is over the content.
     */
    updatePageBreadcrumbOnResize() {
        const headerHeight = this.headerEl.getBoundingClientRect().height;
        this.el.style.setProperty("--o-header-height", `${headerHeight}px`);
    }
}

registry.category("public.interactions").add("website.page_breadcrumb", PageBreadcrumb);

registry.category("public.interactions.edit").add("website.page_breadcrumb", {
    Interaction: PageBreadcrumb,
});
