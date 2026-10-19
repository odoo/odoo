import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const HEADER_SEARCHBAR_SELECTOR = ".o_header_searchbar";
const DIRTY_CLASS = "o_dirty_header_search";

/**
 * The header search bar is rendered outside of any savable area, so the DOM
 * changes made by the searchbar options cannot be saved as view arch. This
 * plugin stores the resulting settings on the website record instead.
 */
export class HeaderSearchbarOptionPlugin extends Plugin {
    static id = "headerSearchbarOption";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dirty_trackers: { selector: HEADER_SEARCHBAR_SELECTOR, dirtyClass: DIRTY_CLASS },
        on_ready_to_save_document_handlers: this.onSave.bind(this),
    };

    async onSave() {
        for (const searchbarEl of this.editable.querySelectorAll(`.${DIRTY_CLASS}`)) {
            const inputEl = searchbarEl.querySelector(".search-query");
            const limit = parseInt(inputEl.dataset.limit);
            await this.services.orm.call(
                "website",
                "set_header_search",
                [this.services.website.currentWebsite.id],
                {
                    search_type: inputEl.dataset.searchType,
                    order_by: inputEl.dataset.orderBy,
                    limit: Number.isNaN(limit) ? 30 : limit,
                }
            );
            searchbarEl.classList.remove(DIRTY_CLASS);
        }
    }
}

registry
    .category("website-plugins")
    .add(HeaderSearchbarOptionPlugin.id, HeaderSearchbarOptionPlugin);
