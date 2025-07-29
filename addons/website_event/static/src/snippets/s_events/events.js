import { DynamicSnippet } from "@website/snippets/s_dynamic_snippet/dynamic_snippet";
import { registry } from "@web/core/registry";

import { groupBy } from "@web/core/utils/arrays";

export class Events extends DynamicSnippet {
    // While the selector has 'upcoming_snippet' in its name, it now has a filter
    // option to include ongoing events. The name is kept for backward compatibility.
    static selector = ".s_event_upcoming_snippet";

    /**
     * @override
     */
    getSearchDomain() {
        let searchDomain = super.getSearchDomain(...arguments);
        const filterByTagIds = this.el.dataset.filterByTagIds;
        if (filterByTagIds) {
            let tagGroupedByCategory = groupBy(JSON.parse(filterByTagIds), "category_id");
            for (const category in tagGroupedByCategory) {
                searchDomain = searchDomain.concat(
                    [["tag_ids", "in", tagGroupedByCategory[category].map(e => e.id)]]);
            }
        }
        return searchDomain;
    }
}

registry
    .category("public.interactions")
    .add("website_event.events", Events);

registry
    .category("public.interactions.edit")
    .add("website_event.events", {
        Interaction: Events,
    });
