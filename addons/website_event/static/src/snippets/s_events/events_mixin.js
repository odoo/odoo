import { groupBy } from "@web/core/utils/arrays";

export const EventsMixin = (T) =>
    class extends T {
        /**
         * @override
         */
        getSearchDomain() {
            let searchDomain = super.getSearchDomain(...arguments);
            const filterByTagIds = this.el.dataset.filterByTagIds;
            if (filterByTagIds) {
                const tagGroupedByCategory = groupBy(JSON.parse(filterByTagIds), "category_id");
                for (const category in tagGroupedByCategory) {
                    searchDomain = searchDomain.concat([
                        ["tag_ids", "in", tagGroupedByCategory[category].map((e) => e.id)],
                    ]);
                }
            }
            return searchDomain;
        }
    };
