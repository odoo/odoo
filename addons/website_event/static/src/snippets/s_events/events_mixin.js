export const EventsMixin = (T) =>
    class extends T {
        /**
         * @override
         */
        getSearchDomain() {
            let searchDomain = super.getSearchDomain(...arguments);
            const filterByTagIds = this.el.dataset.filterByTagIds;
            if (filterByTagIds) {
                const tagGroupedByCategory = Object.groupBy(
                    JSON.parse(filterByTagIds),
                    (tag) => tag.category_id
                );
                for (const tags of Object.values(tagGroupedByCategory)) {
                    searchDomain = searchDomain.concat([["tag_ids", "in", tags.map((e) => e.id)]]);
                }
            }
            return searchDomain;
        }
    };
