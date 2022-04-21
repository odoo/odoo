/** @odoo-module **/

import ListController from 'web.ListController';
import viewRegistry from 'web.view_registry';
import ListView from 'web.ListView';

const WebsitePageListController = ListController.extend({
    /**
     * @override
     */
    _onOpenRecord(event) {
        const record = this.model.get(event.data.id, {raw: true});
        this._goToPage(record.data.url, record.data.website_id);
    },
    /**
     * @override
     */
    _callButtonAction(attrs, record) {
        if (attrs.name === "action_optimize_seo") {
            this._goToPage(record.data.url, record.data.website_id, {
                enable_seo: true,
            });
        } else {
            return this._super(...arguments);
        }
    },
    /**
     * @private
     */
    _goToPage(path, website, options = {}) {
        this.do_action('website.website_editor', {
            additional_context: {
                params: {
                    path: path,
                    website_id: website || '',
                    ...options,
                }
            },
        });
    },
});

const WebsitePageListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: WebsitePageListController,
    }),
});

viewRegistry.add('website_page_list', WebsitePageListView);

export default {
    WebsitePageListController: WebsitePageListController,
    WebsitePageListView: WebsitePageListView,
};
