/** @odoo-module **/

import { registry } from '@web/core/registry';

const websiteSystrayRegistry = registry.category('website_systray');

const unslugHtmlDataObject = (repr) => {
    const match = repr && repr.match(/(.+)\((\d+),(.*)\)/);
    if (!match) {
        return null;
    }
    return {
        model: match[1],
        id: match[2] | 0,
    };
};

export const websiteService = {
    dependencies: ['orm'],
    async start(env, { orm }) {
        let websites = [];
        let currentWebsiteId;

        const setCurrentWebsiteId = id => {
            currentWebsiteId = id;
            websiteSystrayRegistry.trigger('EDIT-WEBSITE');
        };
        return {
            set currentWebsiteId(id) {
                setCurrentWebsiteId(id);
            },
            get currentWebsite() {
                return websites.find(website => website.id === currentWebsiteId);
            },
            get websites() {
                return websites;
            },
            async fetchWebsites() {
                const [currentWebsiteRepr, allWebsites] = await Promise.all([
                    orm.call('website', 'get_current_website'),
                    orm.searchRead('website', []),
                ]);
                websites = [...allWebsites];
                setCurrentWebsiteId(unslugHtmlDataObject(currentWebsiteRepr).id);
            },
        };
    },
};

registry.category('services').add('website', websiteService);
