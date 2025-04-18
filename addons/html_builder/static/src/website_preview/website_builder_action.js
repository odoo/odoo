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
import { registry } from "@web/core/registry";
import { useService, useChildRef } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { WebsiteSystrayItem } from "./website_systray_item";
import { uniqueId } from "@web/core/utils/functions";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { _t } from "@web/core/l10n/translation";
import { AddPageDialog } from "@website/components/dialog/add_page_dialog";
import { Deferred } from "@web/core/utils/concurrency";

export class WebsiteBuilder extends Component {
    static template = "html_builder.WebsiteBuilder";
    static components = { LazyComponent, LocalOverlayContainer };
    static props = { ...standardActionServiceProps };

    setup() {
        this.target = null;
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.websiteService = useService("website");
        this.ui = useService("ui");

        this.websiteContent = useRef("iframe");
        useSubEnv({
            builderRef: useRef("container"),
        });
        this.state = useState({ isEditing: false, key: 1 });
        this.websiteContext = useState(this.websiteService.context);
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
            const [backendWebsiteRepr] = await Promise.all([
                this.orm.call("website", "get_current_website"),
                this.websiteService.fetchWebsites(),
                this.websiteService.fetchUserGroups(),
            ]);
            this.backendWebsiteId = backendWebsiteRepr[0];
            const encodedPath = encodeURIComponent(this.path);
            this.initialUrl = `/website/force/${encodeURIComponent(
                this.backendWebsiteId
            )}?path=${encodedPath}`;
            this.websiteService.currentWebsiteId = this.backendWebsiteId;
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
            this.websiteService.useMysterious = false;
            registry.category("systray").remove("website.WebsiteSystrayItem");
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
        document.querySelector(".o_main_navbar").setAttribute("style", "margin-top: -100%;");
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
        this.resolveIframeLoaded();
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
        document.querySelector(".o_main_navbar").removeAttribute("style");
        this.state.isEditing = isEditing;
        this.addSystrayItems();
    }

    async reloadIframe(isEditing = true, url) {
        this.ui.block();
        this.preparePublicRootReady();
        this.setIframeLoaded();
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
}

registry.category("actions").add("website_preview", WebsiteBuilder);
