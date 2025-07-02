/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { loadBundle } from "@web/core/assets";
import { isVisible } from "@web/core/utils/ui";

import { FullscreenIndication } from '../components/fullscreen_indication/fullscreen_indication';
import { WebsiteLoader } from '../components/website_loader/website_loader';
import { reactive, EventBus } from "@odoo/owl";

const websiteSystrayRegistry = registry.category('website_systray');

// TODO this is duplicated in website_root at least, it should be a shared util
export const unslugHtmlDataObject = (repr) => {
    const match = repr && repr.match(/(.+)\((-?\d+),(.*)\)/);
    if (!match) {
        return null;
    }
    return {
        model: match[1],
        id: match[2] | 0,
    };
};

const ANONYMOUS_PROCESS_ID = 'ANONYMOUS_PROCESS_ID';

export const websiteService = {
    dependencies: ['orm', 'action', 'user', 'dialog', 'hotkey'],
    async start(env, { orm, action, user, dialog, hotkey }) {
        let websites = [];
        let currentWebsiteId;
        let currentMetadata = {};
        let fullscreen;
        let pageDocument;
        let contentWindow;
        let lastUrl;
        let websiteRootInstance;
        let isRestrictedEditor;
        let isDesigner;
        let hasMultiWebsites;
        let actionJsId;
        let blockingProcesses = [];
        let modelNamesProm = null;
        const modelNames = {};
        let invalidateSnippetCache = false;
        let lastWebsiteId = null;

        const context = reactive({
            showNewContentModal: false,
            showResourceEditor: false,
            edition: false,
            isPublicRootReady: false,
            snippetsLoaded: false,
            isMobile: false,
        });
        const bus = new EventBus();

        hotkey.add("escape", () => {
            // Toggle fullscreen mode when pressing escape.
            if (
                (!currentWebsiteId && !fullscreen)
                || (pageDocument && isVisible(pageDocument.querySelector(".modal")))
            ) {
                // Only allow to use this feature while on the website app, or
                // while it is already fullscreen (in case you left the website
                // app in fullscreen mode, thanks to CTRL-K), or if a modal
                // is open within the preview and could be closed with escape.
                return;
            }
            fullscreen = !fullscreen;
            document.body.classList.toggle('o_website_fullscreen', fullscreen);
            bus.trigger(fullscreen ? 'FULLSCREEN-INDICATION-SHOW' : 'FULLSCREEN-INDICATION-HIDE');
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
                if (id && id !== lastWebsiteId) {
                    invalidateSnippetCache = true;
                    lastWebsiteId = id;
                }
                currentWebsiteId = id;
                websiteSystrayRegistry.trigger('EDIT-WEBSITE');
            },
            /**
             * This represents the current website being edited in the
             * WebsitePreview client action. Multiple components based their
             * visibility on this value, which is falsy if the client action is
             * not displayed.
             */
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
                const { dataset } = document.documentElement;
                // XML files have no dataset on Firefox, and an empty one on
                // Chrome.
                const isWebsitePage = dataset && dataset.websiteId;
                if (!isWebsitePage) {
                    currentMetadata = {};
                } else {
                    const { mainObject, seoObject, isPublished, canOptimizeSeo, canPublish, editableInBackend, translatable, viewXmlid } = dataset;
                    // We ignore multiple menus with the same `content_menu_id`
                    // in the DOM, since it's possible to have different
                    // templates for the same content menu (E.g. used for a
                    // different desktop / mobile UI).
                    const contentMenus = [
                        ...new Map(
                            [...document.querySelectorAll("[data-content_menu_id]")].map(
                                (menuEl) => [
                                    menuEl.dataset.content_menu_id,
                                    [menuEl.dataset.menu_name, menuEl.dataset.content_menu_id],
                                ]
                            )
                        ).values(),
                    ];
                    currentMetadata = {
                        path: document.location.href,
                        mainObject: unslugHtmlDataObject(mainObject),
                        seoObject: unslugHtmlDataObject(seoObject),
                        isPublished: isPublished === 'True',
                        canOptimizeSeo: canOptimizeSeo === 'True',
                        canPublish: canPublish === 'True',
                        editableInBackend: editableInBackend === 'True',
                        title: document.title,
                        translatable: !!translatable,
                        contentMenus,
                        // TODO: Find a better way to figure out if
                        // a page is editable or not. For now, we use
                        // the editable selector because it's the common
                        // denominator of editable pages.
                        editable: !!document.getElementById('wrapwrap'),
                        viewXmlid: viewXmlid,
                        lang: document.documentElement.getAttribute('lang').replace('-', '_'),
                        direction: document.documentElement.querySelector('#wrapwrap.o_rtl') ? 'rtl' : 'ltr',
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
            set lastUrl(url) {
                lastUrl = url;
            },
            get lastUrl() {
                return lastUrl;
            },
            get isRestrictedEditor() {
                return isRestrictedEditor === true;
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
            get invalidateSnippetCache() {
                return invalidateSnippetCache;
            },
            set invalidateSnippetCache(value) {
                invalidateSnippetCache = value;
            },

            goToWebsite({ websiteId, path, edition, translation, lang } = {}) {
                this.websiteRootInstance = undefined;
                if (lang) {
                    invalidateSnippetCache = true;
                    path = `/website/lang/${encodeURIComponent(lang)}?r=${encodeURIComponent(path)}`;
                }
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
            async fetchUserGroups() {
                // Fetch user groups, before fetching the websites.
                [isRestrictedEditor, isDesigner, hasMultiWebsites] = await Promise.all([
                    user.hasGroup('website.group_website_restricted_editor'),
                    user.hasGroup('website.group_website_designer'),
                    user.hasGroup('website.group_multi_website'),
                ]);
            },
            async fetchWebsites() {
                websites = [...(await orm.searchRead('website', [], ['domain', 'id', 'name']))];
            },
            async loadWysiwyg() {
                await loadBundle('website.backend_assets_all_wysiwyg');
            },
            blockPreview(showLoader, processId) {
                if (!blockingProcesses.length) {
                    bus.trigger('BLOCK', { showLoader });
                }
                blockingProcesses.push(processId || ANONYMOUS_PROCESS_ID);
            },
            unblockPreview(processId) {
                const processIndex = blockingProcesses.indexOf(processId || ANONYMOUS_PROCESS_ID);
                if (processIndex > -1) {
                    blockingProcesses.splice(processIndex, 1);
                    if (blockingProcesses.length === 0) {
                        bus.trigger('UNBLOCK');
                    }
                }
            },
            showLoader(props) {
                bus.trigger('SHOW-WEBSITE-LOADER', props);
            },
            hideLoader() {
                bus.trigger('HIDE-WEBSITE-LOADER');
            },
            prepareOutLoader() {
                bus.trigger("PREPARE-OUT-WEBSITE-LOADER");
            },
            /**
             * Returns the (translated) "functional" name of a model
             * (_description) given its "technical" name (_name).
             *
             * @param {string} [model]
             * @returns {string}
             */
            async getUserModelName(model = this.currentWebsite.metadata.mainObject.model) {
                if (!modelNamesProm) {
                    // FIXME the `get_available_models` is to be removed/changed
                    // in a near future. This code is to be adapted, probably
                    // with another helper to map a model functional name from
                    // its technical map without the need of the right access
                    // rights (which is why I cannot use search_read here).
                    modelNamesProm = orm.call("ir.model", "get_available_models")
                        .then(modelsData => {
                            for (const modelData of modelsData) {
                                modelNames[modelData['model']] = modelData['display_name'];
                            }
                        })
                        // Precaution in case the util is simply removed without
                        // adapting this method: not critical, we can restore
                        // later and use the fallback until the fix is made.
                        .catch(() => {});
                }
                await modelNamesProm;
                return modelNames[model] || _t("Data");
            },
        };
    },
};

registry.category('services').add('website', websiteService);
