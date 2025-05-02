import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import {
    Component,
    onMounted,
    onWillDestroy,
    onWillStart,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { LazyComponent, loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ResizablePanel } from "@web/core/resizable_panel/resizable_panel";
import { Deferred } from "@web/core/utils/concurrency";
import { uniqueId } from "@web/core/utils/functions";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { effect } from "@web/core/utils/reactive";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { AddPageDialog } from "@website/components/dialog/add_page_dialog";
import { ResourceEditor } from "@website/components/resource_editor/resource_editor";
import { WebsiteSystrayItem } from "./website_systray_item";

export class WebsiteBuilder extends Component {
    static template = "html_builder.WebsiteBuilder";
    static components = { LazyComponent, LocalOverlayContainer, ResizablePanel, ResourceEditor };
    static props = { ...standardActionServiceProps };

    setup() {
        this.target = null;
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.websiteService = useService("website");
        this.ui = useService("ui");
        this.websiteService.websiteRootInstance = undefined;

        this.websiteContent = useRef("iframe");
        useSubEnv({
            builderRef: useRef("container"),
        });
        this.state = useState({ isEditing: false, key: 1 });
        this.websiteContext = useState(this.websiteService.context);
        onMounted(() => {
            // You can't wait for rendering because the Builder depends on the page style synchronously.
            effect(
                (websiteContext) => {
                    if (websiteContext.isMobile) {
                        this.websitePreviewRef.el.classList.add("o_is_mobile");
                    } else {
                        this.websitePreviewRef.el.classList.remove("o_is_mobile");
                    }
                },
                [this.websiteContext]
            );
        });
        // TODO: to remove: this is only needed to not use the website systray
        // when using the "website preview" app.
        this.websiteService.useMysterious = true;
        this.translation = !!this.props.action.context.params?.edit_translations;

        this.overlayRef = useChildRef();
        useSubEnv({
            localOverlayContainerKey: uniqueId("website"),
        });

        this.websitePreviewRef = useRef("website_preview");

        onWillStart(async () => {
            const updateWebsiteId = (websiteId) => {
                const encodedPath = encodeURIComponent(this.path);
                this.initialUrl = `/website/force/${encodeURIComponent(
                    websiteId
                )}?path=${encodedPath}`;
                this.websiteService.currentWebsiteId = websiteId;
            };
            const backendWebsiteId = this.props.action.context.params?.website_id;
            const proms = [
                this.websiteService.fetchWebsites(),
                this.websiteService.fetchUserGroups(),
            ];
            if (backendWebsiteId) {
                updateWebsiteId(backendWebsiteId);
                await Promise.all(proms);
            } else {
                const [backendWebsiteRepr] = await Promise.all([
                    this.orm.call("website", "get_current_website"),
                    ...proms,
                ]);
                updateWebsiteId(backendWebsiteRepr[0]);
            }
        });
        onMounted(() => {
            const { enable_editor, edit_translations } = this.props.action.context.params || {};
            const edition = !!(enable_editor || edit_translations);
            if (edition) {
                this.onEditPage();
            }
        });
        this.publicRootReady = new Deferred();
        this.setIframeLoaded();
        this.addSystrayItems();
        onWillDestroy(() => {
            registry.category("systray").remove("website.WebsiteSystrayItem");
            this.websiteService.useMysterious = false;
            this.websiteService.currentWebsiteId = null;
        });
    }

    get menuProps() {
        const WebsitePlugins = registry.category("website-plugins").getAll();
        return {
            closeEditor: this.reloadIframeAndCloseEditor.bind(this),
            reloadEditor: this.reloadEditor.bind(this),
            snippetsName: "website.snippets",
            toggleMobile: this.toggleMobile.bind(this),
            overlayRef: this.overlayRef,
            isTranslation: this.translation,
            iframeLoaded: this.iframeLoaded,
            isMobile: this.websiteContext.isMobile,
            Plugins: WebsitePlugins,
            config: { initialTarget: this.target },
        };
    }

    get systrayProps() {
        return {
            onNewPage: this.onNewPage.bind(this),
            onEditPage: this.onEditPage.bind(this),
            iframeLoaded: this.iframeLoaded,
        };
    }

    addSystrayItems() {
        registry
            .category("systray")
            .add(
                "website.WebsiteSystrayItem",
                { Component: WebsiteSystrayItem, props: this.systrayProps },
                { sequence: -100 }
            );
    }

    onNewPage() {
        this.dialog.add(AddPageDialog, {
            onAddPage: () => {
                this.websiteService.context.showNewContentModal = false;
            },
            websiteId: this.websiteService.currentWebsite.id,
        });
    }

    async onEditPage() {
        document.querySelector("body").classList.add("o_builder_open");
        await this.iframeLoaded;
        await this.publicRootReady;
        await this.loadAssetsEditBundle();

        setTimeout(() => {
            this.state.isEditing = true;
            registry.category("systray").remove("website.WebsiteSystrayItem");
        }, 200);
    }

    async loadAssetsEditBundle() {
        await Promise.all([
            // TODO Should be website.assets_edit_frontend, but that is currently
            // still used by website, so let's not impact it yet.
            loadBundle("html_builder.assets_edit_frontend", {
                targetDoc: this.websiteContent.el.contentDocument,
            }),
            loadBundle("html_builder.inside_builder_style", {
                targetDoc: this.websiteContent.el.contentDocument,
            }),
        ]);
    }

    onIframeLoad(ev) {
        history.pushState(null, "", ev.target.contentWindow.location.pathname);
        this.websiteService.pageDocument = this.websiteContent.el.contentDocument;
        this.websiteContent.el.setAttribute("is-ready", "true");
        if (this.translation) {
            deleteQueryParam("edit_translations", this.websiteService.contentWindow, true);
        }
        this.preparePublicRootReady();
        this.setupClickListener();
        this.resolveIframeLoaded();
        if (this.props.action.context.params?.with_loader) {
            this.websiteService.hideLoader();
            this.props.action.context.params.with_loader = false;
        }
    }

    setupClickListener() {
        // The clicks on the iframe are listened, so that links with external
        // redirections can be opened in the top window.
        this.websiteContent.el.contentDocument.addEventListener("click", (ev) => {
            const isEditing = this.websiteContext.edition || this.websiteContext.translation;
            if (!isEditing) {
                // Forward clicks to close backend client action's navbar
                // dropdowns.
                this.websiteContent.el.dispatchEvent(new MouseEvent("click", ev));
                /* TODO ?
            } else {
                // When in edit mode, prevent the default behaviours of clicks
                // as to avoid DOM changes not handled by the editor.
                // (Such as clicking on a link that triggers navigating to
                // another page.)
                if (!ev.target.closest("#oe_manipulators")) {
                    ev.preventDefault();
                }
                */
            }
            const linkEl = ev.target.closest("[href]");
            if (!linkEl) {
                return;
            }

            const { href, target /*, classList*/ } = linkEl;
            /* TODO ? If to be done, most likely in a plugin
            if (classList.contains('o_add_language')) {
                ev.preventDefault();
                const searchParams = new URLSearchParams(href);
                this.action.doAction('base.action_view_base_language_install', {
                    target: 'new',
                    additionalContext: {
                        params: {
                            website_id: this.websiteId,
                            url_return: searchParams.get("url_return"),
                        },
                    },
                });
            } else if (classList.contains('js_change_lang') && isEditing) {
                ev.preventDefault();
                const lang = linkEl.dataset['url_code'];
                // The "edit_translations" search param coming from keep_query
                // is removed, and the hash is added.
                const destinationUrl = new URL(href, window.location);
                destinationUrl.searchParams.delete('edit_translations');
                destinationUrl.hash = this.websiteService.contentWindow.location.hash;
                this.websiteService.bus.trigger('LEAVE-EDIT-MODE', {
                    onLeave: () => {
                        this.websiteService.goToWebsite({ path: destinationUrl.toString(), lang });
                    },
                    reloadIframe: false,
                });
            } else
            */
            if (href && target !== "_blank" && !isEditing) {
                if (isTopWindowURL(linkEl)) {
                    ev.preventDefault();
                    browser.location.assign(href);
                } else if (
                    this.websiteContent.el.contentWindow.location.pathname !==
                    new URL(href).pathname
                ) {
                    // This scenario triggers a navigation inside the iframe.
                    this.websiteService.websiteRootInstance = undefined;
                }
            }
        });
    }

    get path() {
        let path = this.props.action.context.params?.path;
        if (path) {
            const url = new URL(path, window.location.origin);
            if (isTopWindowURL(url)) {
                // If the client action is initialized with a path that should
                // not be opened inside the iframe (= something we would want to
                // open on the top window), we consider that this is not a valid
                // flow. Instead of trying to open it on the top window, we
                // initialize the iframe with the website homepage...
                path = "/";
            } else {
                // ... otherwise, the path still needs to be normalized (as it
                // would be if the given path was used as an href of a  <a/>
                // element).
                path = url.pathname + url.search;
            }
        } else {
            path = "/";
        }
        return path;
    }

    async reloadEditor(param) {
        this.target = param.target || null;
        await this.reloadIframe(this.state.isEditing, param.url);
        // trigger an new instance of the builder menu
        this.state.key++;

        this.notification.add(_t("Your modifications were saved to apply this option."), {
            title: _t("Content saved."),
            type: "success",
        });
    }

    async reloadIframeAndCloseEditor() {
        const isEditing = false;
        await this.reloadIframe(isEditing);
        document.querySelector("body").classList.remove("o_builder_open");
        this.state.isEditing = isEditing;
        this.addSystrayItems();
    }

    async reloadIframe(isEditing = true, url) {
        this.ui.block();
        this.preparePublicRootReady();
        this.setIframeLoaded();
        this.websiteService.websiteRootInstance = undefined;
        if (url) {
            this.websiteContent.el.contentWindow.location = url;
        } else {
            this.websiteContent.el.contentWindow.location.reload();
        }
        await this.iframeLoaded;
        if (isEditing) {
            await this.publicRootReady;
            await this.loadAssetsEditBundle();
        }
        this.ui.unblock();
    }

    preparePublicRootReady() {
        const deferred = new Deferred();
        this.publicRootReady = deferred;
        this.websiteContent.el.contentWindow.addEventListener(
            "PUBLIC-ROOT-READY",
            (event) => {
                this.websiteContent.el.setAttribute("is-ready", "true");
                this.websiteService.websiteRootInstance = event.detail.rootInstance;
                deferred.resolve();
            },
            { once: true }
        );
    }

    setIframeLoaded() {
        this.iframeLoaded = new Promise((resolve) => {
            this.resolveIframeLoaded = () => {
                resolve(this.websiteContent.el);
            };
        });
    }

    toggleMobile() {
        // Adding the mobile class directly, to not wait for the component
        // re-rendering.
        this.websiteService.context.isMobile = !this.websiteService.context.isMobile;
    }

    get aceEditorWidth() {
        const storedWidth = browser.localStorage.getItem("ace_editor_width");
        return storedWidth ? parseInt(storedWidth) : 720;
    }

    onResourceEditorResize(width) {
        browser.localStorage.setItem("ace_editor_width", width);
    }
}

function deleteQueryParam(param, target = window, adaptBrowserUrl = false) {
    const url = new URL(target.location.href);
    url.searchParams.delete(param);
    // TODO: maybe to use in the action service
    target.history.replaceState(target.history.state, null, url);
    if (adaptBrowserUrl) {
        deleteQueryParam(param);
    }
}

/**
 * Returns true if the url should be opened in the top
 * window.
 *
 * @param host {string} host of the route.
 * @param pathname {string} path of the route.
 */
function isTopWindowURL({ host, pathname }) {
    for (const fn of registry.category("isTopWindowURL").getAll()) {
        if (fn({ host, pathname })) {
            return true;
        }
    }
    return false;
}

registry
    .category("isTopWindowURL")
    .add("html_builder.website_builder_action", ({ host, pathname }) => {
        const backendRoutes = ["/web", "/web/session/logout", "/odoo"];
        return (
            host !== window.location.host ||
            (pathname &&
                (backendRoutes.includes(pathname) ||
                    pathname.startsWith("/@/") ||
                    pathname.startsWith("/odoo/") ||
                    pathname.startsWith("/web/content/") ||
                    pathname.startsWith("/document/share/")))
        );
    });

registry.category("actions").add("website_preview", WebsiteBuilder);
