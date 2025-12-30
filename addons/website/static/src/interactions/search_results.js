import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { KeepLast } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";
import { parseHTML } from "@html_editor/utils/html";

export class SearchResults extends Interaction {
    static selector = ".container:has(.o_searchbar_result)";
    dynamicContent = {
        ".o_load_more": {
            "t-on-click.prevent": this.loadMore,
        },
    };
    autocompleteMinWidth = 300;

    setup() {
        this.keepLast = new KeepLast();
        this.inputEl = this.el.querySelector(".search-query");
        const orderByEl = this.el.querySelector(".o_search_order_by");
        this.order = orderByEl.value;
        this.limit = parseInt(this.inputEl.dataset.limit) || 6;
    }

    /**
     * Lazy Loading
     */
    async loadMore(ev) {
        const searchType = ev.target.dataset.searchType;
        const offset = parseInt(ev.target.dataset.offset || this.limit);
        // We need displayType = 'columns' by default.
        const row_classes = "o_search_result_item rounded-4";
        const [html, hasMore] = await this.keepLast.add(
            rpc("/website/load_more_search", {
                search: this.inputEl.value,
                search_type: searchType,
                offset: offset,
                limit: this.limit,
                row_classes,
                order: this.order,
                max_nb_chars: Math.round(
                    Math.max(this.autocompleteMinWidth, parseInt(this.inputEl.clientWidth) / 3) *
                        0.22
                ),
            })
        );
        ev.target.classList.add("d-none", !hasMore);
        const doc = parseHTML(document, html);
        const ulEl = ev.target.parentNode.previousElementSibling;
        ulEl.appendChild(doc);
        // Set offset for next loadMore
        ev.target.dataset.offset = offset + this.limit;
    }
}

registry.category("public.interactions").add("website.search_results", SearchResults);
