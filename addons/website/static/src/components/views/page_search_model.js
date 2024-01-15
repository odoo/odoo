/** @odoo-module */

import { useService } from "@web/core/utils/hooks";

import { Domain } from '@web/core/domain';
import { SearchModel } from '@web/search/search_model';

const { onWillStart, useState } = owl;

export class PageSearchModel extends SearchModel {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.website = useService('website');

        this.rpc = useService('rpc');
        this.pagesState = useState({
            pageIds: [],
        });
        onWillStart(async () => {
            // Before the searchModel performs its DB search call, append the
            // website domain to the search domain.
            await this.website.fetchWebsites();
            const website = this.website.currentWebsite || this.website.websites[0];
            this.notifyWebsiteChange(website.id);
        });
    }

    /**
     * @override
     */
    exportState() {
        const state = super.exportState();
        state.pageIds = this.pagesState.pageIds;
        return state;
    }

    /**
     * @override
     */
    _importState(state) {
        super._importState(...arguments);

        if (state.pageIds.length) {
            this.pagesState.pageIds = state.pageIds;
        }
    }

    /**
     * @override
     */
    _getDomain(params = {}) {
        const domain = super._getDomain(params);

        if (!this.pagesState.pageIds.length) {
            return domain;
        }

        const result = Domain.and([
            domain,
            [['id', 'in', this.pagesState.pageIds]]
        ]);

        return params.raw ? result : result.toList();
    }

    /**
     * Updates the pageIds state and notifies the change.
     *
     * @param {number} websiteId - The ID of the website.
     */
    async notifyWebsiteChange(websiteId) {
        // When the website changes, update the pageIds state (which will be
        // added in the base SearchModel domain)
        this.pagesState.pageIds = await this.orm.call(
            "website",
            "get_website_page_ids",
            [websiteId],
        );
        this._notify();
    }
}
