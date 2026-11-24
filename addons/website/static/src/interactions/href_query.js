import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * Restores the query string that the server moved out of dynamic links into
 * `data-href-query`, so that crawlers not executing javascript do not follow
 * every combination of query parameters (see `_move_href_query_to_data`).
 */
export class HrefQuery extends Interaction {
    static selector = "a[data-href-query]";

    start() {
        const href = this.el.getAttribute("href") || "";
        const hashIndex = href.indexOf("#");
        const path = hashIndex === -1 ? href : href.slice(0, hashIndex);
        const hash = hashIndex === -1 ? "" : href.slice(hashIndex);
        this.el.setAttribute("href", `${path}?${this.el.dataset.hrefQuery}${hash}`);
    }
}

registry.category("public.interactions").add("website.href_query", HrefQuery);
