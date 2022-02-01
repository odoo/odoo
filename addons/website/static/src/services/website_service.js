/** @odoo-module **/

import { registry } from '@web/core/registry';

import { FullscreenIndication } from '../components/fullscreen_indication/fullscreen_indication';

const { reactive, EventBus } = owl;

const websiteSystrayRegistry = registry.category('website_systray');

export const unslugHtmlDataObject = (repr) => {
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
    dependencies: ['orm', 'action', 'hotkey'],
    async start(env, { orm, action, hotkey }) {
        let websites = [];
        let currentWebsiteId;
        let currentMetadata = {};
        let fullscreen;
        let pageDocument;
        const context = reactive({
            showNewContentModal: false,
        });
        const bus = new EventBus();

        const setCurrentWebsiteId = id => {
            currentWebsiteId = id;
            websiteSystrayRegistry.trigger('EDIT-WEBSITE');
        };
        hotkey.add("escape", () => {
            // Toggle fullscreen mode when pressing escape.
            if (currentWebsiteId) {
                fullscreen = !fullscreen;
                document.body.classList.toggle('o_website_fullscreen', fullscreen);
                bus.trigger((fullscreen ? 'FULLSCREEN-INDICATION-SHOW' : 'FULLSCREEN-INDICATION-HIDE'));
            }
        });
        registry.category('main_components').add('FullscreenIndication', {
            Component: FullscreenIndication,
            props: { bus },
        });
        return {
            set currentWebsiteId(id) {
                setCurrentWebsiteId(id);
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
            set pageDocument(document) {
                pageDocument = document;
                if (!document) {
                    return;
                }
                const { mainObject, seoObject, isPublished, canPublish, editableInBackend } = document.documentElement.dataset;
                currentMetadata = {
                    path: document.location.href,
                    mainObject: unslugHtmlDataObject(mainObject),
                    seoObject: unslugHtmlDataObject(seoObject),
                    isPublished: isPublished === 'True',
                    canPublish: canPublish === 'True',
                    editableInBackend: editableInBackend === 'True',
                    title: document.title,
                };
                websiteSystrayRegistry.trigger('CONTENT-UPDATED');
            },
            get pageDocument() {
                return pageDocument;
            },
            goToWebsite({ websiteId = currentWebsiteId || websites[0].id, path = '/' } = {}) {
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
