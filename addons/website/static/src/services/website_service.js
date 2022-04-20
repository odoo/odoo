/** @odoo-module **/

import { registry } from '@web/core/registry';
import core from 'web.core';
import ajax from 'web.ajax';
import { getWysiwygClass } from 'web_editor.loader';

const { reactive, EventBus } = owl;

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
    dependencies: ['rpc', 'http', 'action'],
    async start(env, { rpc, http, action }) {
        let websites = [];
        let currentWebsiteId;
        let currentMetadata = {};
        const context = reactive({
            showNewContentModal: false,
            showAceEditor: false,
            edition: false,
            isPublicRootReady: false,
            snippetsLoaded: false,
            isMobile: false,
        });
        let pageDocument;
        let contentWindow;
        let editedObjectPath;
        let websiteRootInstance;
        let Wysiwyg;
        let bus = new EventBus();
        let iframeLocks = 0;
        return {
            set currentWebsiteId(id) {
                currentWebsiteId = id;
                websiteSystrayRegistry.trigger('EDIT-WEBSITE');
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
            get wysiwygLoaded() {
                return !!Wysiwyg;
            },
            goToWebsite({ websiteId, path, edition, translation } = {}) {
                action.doAction('website.website_editor', {
                    clearBreadcrumbs: true,
                    additionalContext: {
                        params: {
                            website_id: websiteId,
                            path,
                            enable_editor: edition,
                            edit_translations: translation,
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
            async loadWysiwyg() {
                if (!Wysiwyg) {
                    await ajax.loadXML('/website/static/src/xml/website.editor.xml', core.qweb);
                    Wysiwyg = await getWysiwygClass({wysiwygAlias: 'website.wysiwyg'}, ['website.compiled_assets_wysiwyg']);
                }
                return Wysiwyg;
            },
            blockIframe() {
              if (iframeLocks === 0) {
                  bus.trigger('BLOCK');
                  iframeLocks++;
              }
            },
            unblockIframe() {
                iframeLocks--
                if (iframeLocks < 0) {
                    iframeLocks = 0;
                }
                if (iframeLocks === 0) {
                    bus.trigger('UNBLOCK');
                }
            }
        };
    },
};

registry.category('services').add('website', websiteService);
