/** @odoo-module **/

import { registry } from '@web/core/registry';
import core from 'web.core';

export const websiteService = {
    dependencies: ['rpc', 'http'],
    async start(env, { rpc, http }) {
        let websites = [];
        return {
            get websites() {
                return websites;
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
