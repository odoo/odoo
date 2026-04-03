export const BlogPostsMixin = (T) =>
    class extends T {
        /**
         * @override
         */
        getSearchDomain() {
            const searchDomain = super.getSearchDomain(...arguments);

            const getParsedIds = (key) => {
                if (!this.el.dataset[key]) {
                    return [];
                }
                const parsed = JSON.parse(this.el.dataset[key]);
                return parsed.map((t) => t.id);
            };

            const filterByTagIds = getParsedIds("filterByTagIds");
            const filterByBlogIds = getParsedIds("filterByBlogIds");
            const filterByAuthorIds = getParsedIds("filterByAuthorIds");

            if (filterByBlogIds.length) {
                searchDomain.push(["blog_id", "in", filterByBlogIds]);
            }
            if (filterByTagIds.length) {
                searchDomain.push(["tag_ids", "in", filterByTagIds]);
            }
            if (filterByAuthorIds.length) {
                searchDomain.push(["author_id", "in", filterByAuthorIds]);
            }
            return searchDomain;
        }
    };
