/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Domain } from '@web/core/domain';
import { SearchModel } from '@web/search/search_model';
import { onWillStart, useState } from "@odoo/owl";

export class PageSearchModel extends SearchModel {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.website = useService('website');

        this.pagesState = useState({
            websiteDomain: false,
        });
        onWillStart(async () => {
            // Before the searchModel performs its DB search call, append the
            // website domain to the search domain.
            await this.website.fetchWebsites();
            const website = await this.getCurrentWebsite();
            await this.notifyWebsiteChange(website.id);
        });
    }

    /**
     * @override
     */
    exportState() {
        const state = super.exportState();
        state.websiteDomain = this.pagesState.websiteDomain;
        return state;
    }

    /**
     * @override
     */
    _importState(state) {
        super._importState(...arguments);

        if (state.websiteDomain) {
            this.pagesState.websiteDomain = state.websiteDomain;
        }
    }

    /**
     * @override
     */
    _getDomain(params = {}) {
        let domain = super._getDomain(params);
        if (!this.pagesState.websiteDomain) {
            return domain;
        }

        domain = Domain.and([
            domain,
            this.pagesState.websiteDomain,
        ]);
        return params.raw ? domain : domain.toList();
    }

    /**
     * Updates the website domain state and notifies the change. That domain
     * state will be appended to the base SearchModel domain.
     *
     * @param {number} websiteId - The ID of the website.
     */
    async notifyWebsiteChange(websiteId) {
        let websiteDomain = [];
        if (websiteId && 'website_id' in this.searchViewFields) {
            if (this.resModel === 'website.page') {
                // In case of `website.page`, we can't find the website pages
                // with a regular domain (because we need to filter duplicates).
                const pageIds = await this.orm.call(
                    "website",
                    "get_website_page_ids",
                    [websiteId],
                );
                websiteDomain = [['id', 'in', pageIds]];
            } else {
                websiteDomain = [['website_id', 'in', [false, websiteId]]];
            }
        }
        this.pagesState.websiteDomain = websiteDomain;
        this._notify();
    }

    /**
     * Retrieves the current website.
     *
     * @returns {Object} The current website.
     */
    async getCurrentWebsite() {
        const currentWebsite = (await this.orm.call('website', 'get_current_website')).match(/\d+/);
        if (currentWebsite) {
            return this.website.websites.find(w => w.id === parseInt(currentWebsite[0]));
        }
        return this.website.websites[0];
    }
}
