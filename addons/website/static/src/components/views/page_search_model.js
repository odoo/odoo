import { useService } from "@web/core/utils/hooks";
import { SearchModel } from "@web/search/search_model";

export class PageSearchModel extends SearchModel {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.website = useService("website");
    }

    /**
     * @override
     */
    async load() {
        await super.load(...arguments);

        // Call `fetchWebsites` to populate `this.website.websites`.
        await this.website.fetchWebsites();

        if (this.searchViewFields.website_id) {
            await this.createFilterForAllWebsites();
            await this.selectCurrentWebsiteFilter();
        }
    }

    /**
     * Creates filter for all available websites.
     */
    async createFilterForAllWebsites() {
        const existingWebsiteFilters = this.getSearchItems(
            (searchItem) => searchItem.type === "filter" && searchItem.name.startsWith("website_")
        );

        // Check if filters are already created
        if (existingWebsiteFilters.length === this.website.websites.length) {
            return;
        }

        let websitePageIds = {};
        if (this.resModel === "website.page") {
            const websiteIds = this.website.websites.map((website) => website.id);
            websitePageIds = await this.orm.call("website", "get_website_page_ids", [websiteIds]);
        }

        const websiteFilters = this.website.websites.map((website) => {
            const websiteDomain =
                this.resModel === "website.page"
                    ? [["id", "in", websitePageIds[website.id] || []]]
                    : [["website_id", "in", [false, website.id]]];

            return {
                name: `website_${website.id}`,
                description: website.name,
                domain: websiteDomain,
                type: "filter",
            };
        });

        this._createGroupOfSearchItems(websiteFilters);
    }

    /**
     * Selects the current website filter if no other website filter is active.
     */
    async selectCurrentWebsiteFilter() {
        const currentlySelectedWebsiteFilters = this.getSearchItems(
            (searchItem) =>
                searchItem.type === "filter" &&
                searchItem.name.startsWith("website_") &&
                searchItem.isActive
        );
        if (currentlySelectedWebsiteFilters.length) {
            return;
        }

        const currentWebsite = await this.getCurrentWebsite();
        const [currentWebsiteFilter] = this.getSearchItems(
            (searchItem) =>
                searchItem.type === "filter" && searchItem.name === `website_${currentWebsite.id}`
        );
        if (currentWebsiteFilter) {
            this.toggleSearchItem(currentWebsiteFilter.id);
        }
    }

    /**
     * Retrieves the current website.
     *
     * @returns {Object} The current website.
     */
    async getCurrentWebsite() {
        const currentWebsite = await this.orm.call("website", "get_current_website");
        if (currentWebsite) {
            return this.website.websites.find((w) => w.id === currentWebsite[0]);
        }
        return this.website.websites[0];
    }
}
