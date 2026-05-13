import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";

/**
 * Radio inputs can encode a single param in their value
 * (e.g. "country_all=True" or "is_remote=1").
 * Returns null for all other input types.
 */
function parseEncodedRadioValue(inputEl) {
    if (inputEl.type !== "radio" || !inputEl.value.includes("=")) {
        return null;
    }
    const [[name, value]] = new URLSearchParams(inputEl.value).entries();
    return { name, value };
}

/**
 * Collects active filter values from all inputs in the container.
 *
 * Returns:
 *   params — the filter key/values to apply to the URL
 *   clearParams — param names to wipe from the existing URL search string,
 *                 so stale values from a previous filter state don't bleed
 *                 through.
 */
function collectMobileFilterParams(containerEl) {
    const params = new URLSearchParams();
    const clearParams = new Set(["prevent_redirect"]);
    const selectedTags = new Set();

    for (const inputEl of containerEl.querySelectorAll("input")) {
        if (!inputEl.name || inputEl.disabled) {
            continue;
        }
        // We will rebuild the entire query string from scratch, so all params
        // corresponding to inputs in the offcanvas should be cleared from the
        // existing URL.
        clearParams.add(inputEl.name);
        const encodedParam = parseEncodedRadioValue(inputEl);
        if (encodedParam) {
            // If this is a radio input with an encoded value, we need to clear
            // both the param in the encoded value and the param corresponding
            // to the input name, since the input name is not included in the
            // encoded value (e.g. "country_all=True").
            clearParams.add(encodedParam.name);
        }

        // For checkboxes and radios, only include the value if they're checked.
        // Checked radios with an encoded value are handled separately below.
        const isToggle = inputEl.type === "checkbox" || inputEl.type === "radio";
        if (isToggle && !inputEl.checked) {
            continue;
        }
        if (inputEl.name === "tags") {
            selectedTags.add(inputEl.dataset.slug || inputEl.value);
            continue;
        }
        if (encodedParam) {
            const { name, value } = encodedParam;
            // Param names starting with "all_" (e.g. "all_department") are
            // reset signals, not real filter values — skip them.
            if (value && !name.startsWith("all_")) {
                params.append(name, value);
            }
            continue;
        }
        if (inputEl.value) {
            params.append(inputEl.name, inputEl.value);
        }
    }
    if (selectedTags.size) {
        params.set("tags", [...selectedTags].join(","));
    }
    return { params, clearParams };
}

/**
 * Appends a segment to a URL pathname, stripping any trailing slash first.
 * e.g. appendPathSegment(url, "tags", "culture") → /event/tags/culture
 */
function appendPathSegment(url, ...segments) {
    url.pathname = [url.pathname.replace(/\/$/, ""), ...segments].join("/");
}

/**
 * Build the URL corresponding to the current filter state.
 *
 * Filter params may be represented either in the URL path or in the
 * query string, depending on the offcanvas configuration. Existing
 * query params are preserved unless listed in clearParams.
 *
 * Returns a relative URL suitable for redirecting to the filtered page.
 */
function buildFilterUrl(offcanvasEl, { params, clearParams }) {
    const url = new URL(
        offcanvasEl.dataset.filterUrl || window.location.pathname,
        window.location.origin
    );
    const search = new URLSearchParams(window.location.search);
    clearParams.forEach((name) => search.delete(name));

    // For any param names listed in the offcanvas's filterPathParams dataset,
    // move them from the query string into the URL path. This is because some
    // pages have filter-specific URL structures that expect certain params
    // to be in the path (e.g. /event/tags/culture instead of /jobs?is_remote=1)
    const pathParamNames = (offcanvasEl.dataset.filterPathParams || "").split(",").filter(Boolean);
    const paramsMovedToPath = new Set();

    for (const name of pathParamNames) {
        const value = params.get(name);
        if (!value) {
            continue;
        }
        appendPathSegment(url, name, value);
        paramsMovedToPath.add(name);
    }

    // If the offcanvas has a filterTagPath dataset and tags were selected,
    // append the tags to the URL path.
    const tags = params.get("tags");
    if (offcanvasEl.dataset.filterTagPath && tags) {
        appendPathSegment(url, offcanvasEl.dataset.filterTagPath, tags);
        paramsMovedToPath.add("tags");
        // This is a special param that the backend uses to detect that the
        // request is coming from a filter change, and not from a full page
        // reload. It prevents the backend from redirecting to the canonical URL
        // (e.g. /event instead of /event/tags/culture), which would cause the
        // filters to be lost.
        search.set("prevent_redirect", "True");
    }

    // Append any remaining params to the search string.
    for (const [name, value] of params) {
        if (!paramsMovedToPath.has(name)) {
            search.append(name, value);
        }
    }

    url.search = search.toString();
    return `${url.pathname}${url.search}`;
}

export class MobileFilterButtons extends Interaction {
    static selector = ".offcanvas-footer";

    dynamicContent = {
        ".o_mobile_filter_apply": { "t-on-click.prevent": this.onApplyFilters },
        ".o_mobile_filter_clear": { "t-on-click.prevent": this.onClearFilters },
    };

    onApplyFilters() {
        const offcanvasEl = this.el.closest(".o_website_offcanvas, .offcanvas");
        redirect(buildFilterUrl(offcanvasEl, collectMobileFilterParams(offcanvasEl)));
    }

    onClearFilters() {
        const offcanvasEl = this.el.closest(".o_website_offcanvas, .offcanvas");
        redirect(offcanvasEl.dataset.filterUrl || window.location.pathname);
    }
}

registry.category("public.interactions").add("website.mobile_filter_buttons", MobileFilterButtons);
