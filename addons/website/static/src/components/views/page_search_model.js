import { useService } from "@web/core/utils/hooks";
import { SearchModel } from '@web/search/search_model';
import { onWillStart } from "@odoo/owl";

export class PageSearchModel extends SearchModel {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.website = useService('website');

        onWillStart(async () => {
            // Call `fetchWebsites` to populate `this.website.websites`.
            await this.website.fetchWebsites();

            await this.addFilterForAllWebsites();
            await this.selectFilterForCurrentWebsite();
        });
    }

    /**
     * Adds filters for all available websites if they haven't been added
     * already.
     */
    async addFilterForAllWebsites() {
        const existingWebsiteFilters = this.getSearchItems(
            (searchItem) => searchItem.type === "filter" && searchItem.name.startsWith("website_")
        );

        // Skip adding filters if filter for all the websites is already added
        if (existingWebsiteFilters.length === this.website.websites.length) {
            return;
        }

        const websiteFilters = this.website.websites.map(async (website) => {
            let websiteDomain = [];

            if (this.resModel === "website.page") {
                // `website.page` requires fetching specific page IDs, as a
                // standard domain filter cannot be used due to duplicate
                // entries.
                const pageIds = await this.orm.call("website", "get_website_page_ids", [
                    website.id,
                ]);
                websiteDomain = [["id", "in", pageIds]];
            } else {
                websiteDomain = [["website_id", "in", [false, website.id]]];
            }

            return {
                description: website.name,
                domain: websiteDomain,
                name: `website_${website.id}`,
                type: "filter",
            };
        });

        this._createGroupOfSearchItems(await Promise.all(websiteFilters));
    }

    /**
     * Selects the filter for the current website if no other website filter is
     * selected.
     */
    async selectFilterForCurrentWebsite() {
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
        const currentWebsiteFilter = this.getSearchItems(
            (searchItem) =>
                searchItem.type === "filter" && searchItem.name === `website_${currentWebsite.id}`
        )[0];
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
        const currentWebsite = await this.orm.call('website', 'get_current_website');
        if (currentWebsite) {
            return this.website.websites.find(w => w.id === currentWebsite[0]);
        }
        return this.website.websites[0];
    }
}
