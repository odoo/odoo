import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PageBreadcrumb extends Interaction {
    static selector = "div.o_page_breadcrumb";
    dynamicContent = {
        _window: {
            "t-on-resize": this._updatePageBreadcrumbOnResize,
        },
    };

    start() {
        //need to adjust breadcrumb when page is loaded and interaction initiates
        this._updatePageBreadcrumbOnResize();
    }
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Called when the window is resized
     *
     * @private
     */
    _updatePageBreadcrumbOnResize() {
        const wrapwrapEl = document.querySelector("div#wrapwrap");
        const headerHeight = wrapwrapEl
            ?.querySelector("header#top")
            ?.getBoundingClientRect().height;
        if (headerHeight && wrapwrapEl.classList.contains("o_header_overlay")) {
            this.el.style.top = `${headerHeight}px`;
        }
    }
}

registry.category("public.interactions").add("website.page_breadcrumb", PageBreadcrumb);

registry.category("public.interactions.edit").add("website.page_breadcrumb", {
    Interaction: PageBreadcrumb,
});
