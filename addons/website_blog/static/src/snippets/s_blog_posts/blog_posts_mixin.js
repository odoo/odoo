export const BlogPostsMixin = (T) =>
    class extends T {
        /**
         * @override
         */
        getSearchDomain() {
            const searchDomain = super.getSearchDomain(...arguments);
            const filterByBlogId = parseInt(this.el.dataset.filterByBlogId);
            if (filterByBlogId >= 0) {
                searchDomain.push(["blog_id", "=", filterByBlogId]);
            }
            return searchDomain;
        }
    };
