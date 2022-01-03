/** @odoo-module **/

import { registry } from '@web/core/registry';

const { reactive } = owl;

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
    dependencies: ['orm', 'action'],
    async start(env, { orm, action }) {
        let websites = [];
        let currentWebsiteId;
        let currentMetadata = {};
        const context = reactive({
            showNewContentModal: false,
        });

        const setCurrentWebsiteId = id => {
            currentWebsiteId = id;
            websiteSystrayRegistry.trigger('EDIT-WEBSITE');
        };
        return {
            set currentWebsiteId(id) {
                setCurrentWebsiteId(id);
            },
            set currentMetadata(metadata) {
                currentMetadata = metadata;
            },
            get currentWebsite() {
                const currentWebsite = websites.find(w => w.id === currentWebsiteId);
                if (currentWebsite) {
                    currentWebsite.metadata = currentMetadata;
                }
                return currentWebsite;
            },
            get websites() {
                return websites;
            },
            get context() {
                return context;
            },
            goToWebsite({ websiteId = currentWebsiteId || websites[0].id, path = '/' }) {
                action.doAction('website.website_preview', {
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
