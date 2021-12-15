/** @odoo-module **/

import { registry } from '@web/core/registry';

export const websiteService = {
    dependencies: ['orm'],
    async start(env, { orm }) {
        let websites = [];
        return {
            get websites() {
                return websites;
            },
            async fetchWebsites() {
                const allWebsites = await orm.searchRead('website', []);
                websites = [...allWebsites];
            },
        };
    },
};

registry.category('services').add('website', websiteService);
