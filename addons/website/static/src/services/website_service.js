/** @odoo-module **/

import { registry } from '@web/core/registry';
import core from 'web.core';
import ajax from 'web.ajax';
import { getWysiwygClass } from 'web_editor.loader';

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
    dependencies: ['orm', 'action', 'user', 'dialog', 'hotkey'],
    async start(env, { orm, action, user, dialog, hotkey }) {
        let websites = [];
        let currentWebsiteId;
        let currentMetadata = {};
        let fullscreen;
        let pageDocument;
        let contentWindow;
        let editedObjectPath;
        let websiteRootInstance;
        let Wysiwyg;
        const context = reactive({
            showNewContentModal: false,
            showAceEditor: false,
            edition: false,
            isPublicRootReady: false,
            snippetsLoaded: false,
            isMobile: false,
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
            get bus() {
                return bus;
            },
            set pageDocument(document) {
                pageDocument = document;
                if (!document) {
                    return;
                }
                const { mainObject, seoObject, isPublished, canPublish, editableInBackend, translatable } = document.documentElement.dataset;
                currentMetadata = {
                    path: document.location.href,
                    mainObject: unslugHtmlDataObject(mainObject),
                    seoObject: unslugHtmlDataObject(seoObject),
                    isPublished: isPublished === 'True',
                    canPublish: canPublish === 'True',
                    editableInBackend: editableInBackend === 'True',
                    title: document.title,
                    translatable: !!translatable,
                };
                websiteSystrayRegistry.trigger('CONTENT-UPDATED');
            },
            get pageDocument() {
                return pageDocument;
            },
            set contentWindow(window) {
                contentWindow = window;
            },
            get contentWindow() {
                return contentWindow;
            },
            get websiteRootInstance() {
                return websiteRootInstance;
            },
            set websiteRootInstance(rootInstance) {
                websiteRootInstance = rootInstance;
                context.isPublicRootReady = !!rootInstance;
            },
            set editedObjectPath(path) {
                editedObjectPath = path;
            },
            get editedObjectPath() {
                return editedObjectPath;
            },
            isPublisher() {
                return user.hasGroup('website.group_website_publisher');
            },
            openMenuDialog(Component, props) {
                return dialog.add(Component, props);
            },
            goToWebsite({ websiteId, path, edition, translation } = {}) {
                action.doAction('website.website_preview', {
                    clearBreadcrumbs: true,
                    additionalContext: {
                        params: {
                            website_id: websiteId || currentWebsiteId,
                            path: path || (contentWindow && contentWindow.location.href) || '/',
                            enable_editor: edition,
                            edit_translations: translation,
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
            async loadWysiwyg() {
                if (!Wysiwyg) {
                    await ajax.loadXML('/website/static/src/xml/website.editor.xml', core.qweb);
                    Wysiwyg = await getWysiwygClass({wysiwygAlias: 'website.wysiwyg'}, ['website.compiled_assets_wysiwyg']);
                }
                return Wysiwyg;
            },
            blockIframe(showLoader = true, loaderDelay = 0) {
                bus.trigger('BLOCK', {showLoader, loaderDelay});
            },
            unblockIframe() {
                bus.trigger('UNBLOCK');
            }
        };
    },
};

registry.category('services').add('website', websiteService);
