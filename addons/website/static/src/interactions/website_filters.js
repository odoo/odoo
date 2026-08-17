import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
import { Interaction } from "@web/public/interaction";

/**
 * Applies the filters of a website listing page without reloading it.
 *
 * Every control carries in `data-filter-url` the URL it leads to, built server
 * side, so no filter encoding lives here: fetch that URL and swap the regions
 * listed in `data-filter-refresh`. The panel being one of them, its options and
 * counters are re-rendered against the new selection while it stays open.
 */
export class WebsiteFilters extends Interaction {
    static selector = ".o_website_filters";

    dynamicContent = {
        "[data-filter-url]": {
            "t-on-click": (ev) => this.applyFilters(ev.currentTarget.dataset.filterUrl),
        },
        _window: {
            "t-on-popstate": this.onPopState,
        },
    };

    setup() {
        this.refreshSelectors = this.el.dataset.filterRefresh
            .split(",")
            .map((selector) => selector.trim())
            .filter(Boolean);
        this.hasPushedState = false;
    }

    onPopState(ev) {
        if (this.hasPushedState) {
            this.applyFilters(ev.state?.filterUrl || browser.location.href);
        }
    }

    async applyFilters(url) {
        const loadingEl = this.el.querySelector(".offcanvas-body");
        loadingEl.classList.add("opacity-50", "pe-none");

        let newDocument;
        try {
            const response = await this.waitFor(browser.fetch(url));
            if (!response.ok) {
                throw new Error(response.statusText);
            }
            const content = await this.waitFor(response.text());
            newDocument = new DOMParser().parseFromString(content, "text/html");
        } catch {
            redirect(url);
            return;
        }
        loadingEl.classList.remove("opacity-50", "pe-none");

        const regions = this.refreshSelectors
            .map((selector) => [
                document.querySelector(selector),
                newDocument.querySelector(selector),
            ])
            .filter(([currentEl, newEl]) => currentEl && newEl);

        const interactions = this.services["public.interactions"];
        for (const [currentEl, newEl] of regions) {
            if (currentEl !== this.el) {
                interactions.stopInteractions(currentEl);
            }
            currentEl.replaceChildren(...newEl.childNodes);
        }

        const displayedUrl = new URL(url, browser.location.href);
        displayedUrl.searchParams.delete("pinned_tag");
        if (displayedUrl.href !== browser.location.href) {
            history.pushState({ filterUrl: url }, "", displayedUrl.href);
            this.hasPushedState = true;
        }

        for (const [currentEl] of regions) {
            if (currentEl !== this.el) {
                interactions.startInteractions(currentEl);
            }
        }
    }
}

registry.category("public.interactions").add("website.website_filters", WebsiteFilters);
