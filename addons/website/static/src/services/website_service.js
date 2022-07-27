/** @odoo-module **/

import { registry } from '@web/core/registry';
import core from 'web.core';
import ajax from 'web.ajax';
import { getWysiwygClass } from 'web_editor.loader';

import { FullscreenIndication } from '../components/fullscreen_indication/fullscreen_indication';
import { WebsiteLoader } from '../components/website_loader/website_loader';

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
        let isPublisher;
        let isDesigner;
        let hasMultiWebsites;
        let actionJsId;
        const context = reactive({
            showNewContentModal: false,
            showAceEditor: false,
            edition: false,
            isPublicRootReady: false,
            snippetsLoaded: false,
            isMobile: false,
            showPageProperties: false,
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
        }, { global: true });
        registry.category('main_components').add('FullscreenIndication', {
            Component: FullscreenIndication,
            props: { bus },
        });
        registry.category('main_components').add('WebsiteLoader', {
            Component: WebsiteLoader,
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
                    currentMetadata = {};
                    contentWindow = null;
                    return;
                }
                // Not all files have a dataset. (e.g. XML)
                if (!document.documentElement.dataset) {
                    currentMetadata = {};
                } else {
                    const { mainObject, seoObject, isPublished, canPublish, editableInBackend, translatable, viewXmlid } = document.documentElement.dataset;
                    const contentMenuEl = document.querySelector('[data-content_menu_id]');
                    currentMetadata = {
                        path: document.location.href,
                        mainObject: unslugHtmlDataObject(mainObject),
                        seoObject: unslugHtmlDataObject(seoObject),
                        isPublished: isPublished === 'True',
                        canPublish: canPublish === 'True',
                        editableInBackend: editableInBackend === 'True',
                        title: document.title,
                        translatable: !!translatable,
                        contentMenuId: contentMenuEl && contentMenuEl.dataset.content_menu_id,
                        // TODO: Find a better way to figure out if
                        // a page is editable or not. For now, we use
                        // the editable selector because it's the common
                        // denominator of editable pages.
                        editable: !!document.getElementById('wrapwrap'),
                        viewXmlid: viewXmlid,
                    };
                }
                contentWindow = document.defaultView;
                websiteSystrayRegistry.trigger('CONTENT-UPDATED');
            },
            get pageDocument() {
                return pageDocument;
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
            get isPublisher() {
                return isPublisher === true;
            },
            get isDesigner() {
                return isDesigner === true;
            },
            get hasMultiWebsites() {
                return hasMultiWebsites === true;
            },
            get actionJsId() {
                return actionJsId;
            },
            set actionJsId(jsId) {
                actionJsId = jsId;
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
                // Fetch user groups, before fetching the websites.
                [isPublisher, isDesigner, hasMultiWebsites] = await Promise.all([
                    user.hasGroup('website.group_website_publisher'),
                    user.hasGroup('website.group_website_designer'),
                    user.hasGroup('website.group_multi_website'),
                ]);

                const [currentWebsiteRepr, allWebsites] = await Promise.all([
                    orm.call('website', 'get_current_website'),
                    hasMultiWebsites ? orm.searchRead('website', [], ['domain', 'id', 'name']) : [],
                ]);
                websites = [...allWebsites];
                setCurrentWebsiteId(unslugHtmlDataObject(currentWebsiteRepr).id);
                if (!websites.length) {
                    websites = [{ id: currentWebsiteId }];
                }
            },
            async loadWysiwyg() {
                if (!Wysiwyg) {
                    await ajax.loadXML('/website/static/src/xml/website.editor.xml', core.qweb);
                    Wysiwyg = await getWysiwygClass({wysiwygAlias: 'website.wysiwyg'}, ['website.compiled_assets_wysiwyg']);
                }
                return Wysiwyg;
            },
            blockIframe(showLoader = true, loaderDelay = 0, processId) {
                bus.trigger('BLOCK', {showLoader, loaderDelay, processId});
            },
            unblockIframe(processId) {
                bus.trigger('UNBLOCK', { processId });
            },
            leaveEditMode() {
                // FIXME this does not care about if the page is dirty or not.

                // TODO this should not be needed here, the one who was in
                // charge of adding this class should be the one in charge of
                // removing it.
                document.body.classList.remove('editor_has_snippets');
                context.snippetsLoaded = false;
                context.edition = false;
            },
            showLoader(props) {
                bus.trigger('SHOW-WEBSITE-LOADER', props);
            },
            hideLoader() {
                bus.trigger('HIDE-WEBSITE-LOADER');
            },
        };
    },
};

registry.category('services').add('website', websiteService);
