/** @odoo-module **/

import { registry } from '@web/core/registry';
import core from 'web.core';

const websiteSystrayRegistry = registry.category('website_systray');

export const websiteService = {
    dependencies: ['rpc', 'http', 'action'],
    async start(env, { rpc, http, action }) {
        let websites = [];
        let currentWebsiteId;
        return {
            set currentWebsiteId(id) {
                currentWebsiteId = id;
                websiteSystrayRegistry.trigger('EDIT-WEBSITE');
            },
            get currentWebsite() {
                return websites.find(website => website.id === currentWebsiteId);
            },
            get websites() {
                return websites;
            },
            goToWebsite({ websiteId = currentWebsiteId || websites[0].id, path = '/' }) {
                action.doAction('website.website_editor', {
                    clearBreadcrumbs: true,
                    additionalContext: {
                        params: {
                            website_id: websiteId,
                            path,
                        },
                    },
                });
            },
            async fetchWebsites() {
                websites = await rpc('/website/get_websites');
            },
            async sendRequest(route, params, readMethod = "text", method = "post") {
                return http[method](route, { ...params, 'csrf_token': core.csrf_token }, readMethod);
            },
        };
    },
};

registry.category('services').add('website', websiteService);
