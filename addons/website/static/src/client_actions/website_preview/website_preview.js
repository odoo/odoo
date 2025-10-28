/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from '@web/core/browser/browser';
import { registry } from '@web/core/registry';
import { ResizablePanel } from '@web/core/resizable_panel/resizable_panel';
import { useService, useBus } from '@web/core/utils/hooks';
import { redirect } from "@web/core/utils/urls";
import { session } from "@web/session";
import { ResourceEditor } from '../../components/resource_editor/resource_editor';
import { WebsiteEditorComponent } from '../../components/editor/editor';
import { WebsiteTranslator } from '../../components/translator/translator';
import { unslugHtmlDataObject } from '../../services/website_service';
import {OptimizeSEODialog} from '@website/components/dialog/seo';
import { WebsiteDialog } from "@website/components/dialog/dialog";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import wUtils from '@website/js/utils';
import { renderToElement } from "@web/core/utils/render";
import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import {
    Component,
    onWillStart,
    onMounted,
    onWillUnmount,
    useRef,
    useEffect,
    useState,
    useExternalListener,
} from "@odoo/owl";
import { getScrollingElement } from "@web/core/utils/scrolling";
import { isBrowserMicrosoftEdge } from "@web/core/browser/feature_detection";

class BlockPreview extends Component {
    static template = "website.BlockPreview";
    static props = {};
}

export class WebsitePreview extends Component {
    static template = "website.WebsitePreview";
    static components = {
        WebsiteEditorComponent,
        BlockPreview,
        WebsiteTranslator,
        ResourceEditor,
        ResizablePanel,
    };
    static props = { ...standardActionServiceProps };
    setup() {
        this.websiteService = useService('website');
        this.dialogService = useService('dialog');
        this.title = useService('title');
        this.action = useService('action');
        this.orm = useService('orm');

        this.iframeFallbackUrl = '/website/iframefallback';

        this.iframe = useRef('iframe');
        this.iframefallback = useRef('iframefallback');
        this.container = useRef('container');
        this.websiteContext = useState(this.websiteService.context);
        this.blockedState = useState({
            isBlocked: false,
            showLoader: false,
        });
        // The params used to configure the context should be ignored when the
        // action is restored (example: click on the breadcrumb).
        this.isRestored = this.props.action.jsId === this.websiteService.actionJsId;
        this.websiteService.actionJsId = this.props.action.jsId;

        useBus(this.websiteService.bus, 'BLOCK', (event) => this.block(event.detail));
        useBus(this.websiteService.bus, 'UNBLOCK', () => this.unblock());
        useExternalListener(window, "keydown", this._onKeydownRefresh.bind(this));

        onWillStart(async () => {
            const [backendWebsiteRepr] = await Promise.all([
                this.orm.call('website', 'get_current_website'),
                this.websiteService.fetchWebsites(),
                this.websiteService.fetchUserGroups(),
            ]);
            this.backendWebsiteId = unslugHtmlDataObject(backendWebsiteRepr).id;

            const encodedPath = encodeURIComponent(this.path);
            if (!session.website_bypass_domain_redirect // Used by the Odoo support (bugs to be expected)
                    // As a stable fix, we chose to never redirect to the right
                    // domain anymore in this case. We still do when using the
                    // website switcher, but not when reaching the "default"
                    // website. The goal is to better support users typing
                    // mysupercompany.odoo.com explicitly to enter their
                    // backend instead of mysupercompany.be.
                    // Bugs are to be expected while editing/using the website
                    // mysupercompany.be from mysupercompany.odoo.com though,
                    // but it should be the case only in specific/advanced
                    // situations.
                    // TODO remove this code properly in master.
                    && 1 === 0
                    && this.websiteDomain
                    && !wUtils.isHTTPSorNakedDomainRedirection(this.websiteDomain, window.location.origin)) {
                // The website domain might be the naked one while the naked one
                // is actually redirecting to `www` (or the other way around).
                // In such a case, we need to consider those 2 from the same
                // domain and let the iframe load that "different" domain. The
                // iframe will actually redirect to the correct one (naked/www),
                // which will ends up with the same domain as the parent window
                // URL (event if it wasn't, it wouldn't be an issue as those are
                // really considered as the same domain, the user will share the
                // same session and CORS errors won't be a thing in such a case)
                this.dialogService.add(WebsiteDialog, {
                    title: _t("Redirecting..."),
                    body: _t("You are about to be redirected to the domain configured for your website ( %s ). This is necessary to edit or view your website from the Website app. You might need to log back in.", this.websiteDomain),
                    showSecondaryButton: false,
                }, {
                    onClose: () => {
                        window.location.href = `${encodeURI(this.websiteDomain)}/odoo/action-website.website_preview?path=${encodedPath}&website_id=${encodeURIComponent(this.websiteId)}`;
                    }
                });
            } else {
                this.initialUrl = `/website/force/${encodeURIComponent(this.websiteId)}?path=${encodedPath}`;
            }
        });

        useEffect(() => {
            this.websiteService.currentWebsiteId = this.websiteId;
            if (this.isRestored) {
                return;
            }

            const isScreenLargeEnoughForEdit =
                uiUtils.getSize() >= SIZES.MD;
            if (!isScreenLargeEnoughForEdit && this.props.action.context.params) {
                this.props.action.context.params.enable_editor = false;
                this.props.action.context.params.with_loader = false;
            }

            this.websiteService.context.showNewContentModal = this.props.action.context.params && this.props.action.context.params.display_new_content;
            this.websiteService.context.edition = this.props.action.context.params && !!this.props.action.context.params.enable_editor;
            this.websiteService.context.translation = this.props.action.context.params && !!this.props.action.context.params.edit_translations;
            if (this.props.action.context.params && this.props.action.context.params.enable_seo) {
                this.iframe.el.addEventListener('load', () => {
                    this.websiteService.pageDocument = this.iframe.el.contentDocument;
                    this.dialogService.add(OptimizeSEODialog);
                }, {once: true});
            }
            if (this.props.action.context.params && this.props.action.context.params.with_loader) {
                this.websiteService.showLoader({ showTips: true });
            }
        }, () => [this.props.action.context.params]);

        useEffect(() => {
            this.websiteContext.showResourceEditor = false;
        }, () => [
            this.websiteContext.showNewContentModal,
            this.websiteContext.edition,
            this.websiteContext.translation,
        ]);

        onMounted(() => {
            this.websiteService.blockPreview(true, 'load-iframe');
            this.iframe.el.addEventListener('load', () => this.websiteService.unblockPreview('load-iframe'), { once: true });
            // For a frontend page, it is better to use the
            // OdooFrameContentLoaded event to unblock the iframe, as it is
            // triggered faster than the load event.
            this.iframe.el.addEventListener('OdooFrameContentLoaded', () => this.websiteService.unblockPreview('load-iframe'), { once: true });
        });

        onWillUnmount(() => {
            this.websiteService.context.showResourceEditor = false;
            const { pathname, search, hash } = this.iframe.el.contentWindow.location;
            this.websiteService.lastUrl = `${pathname}${search}${hash}`;
            this.websiteService.currentWebsiteId = null;
            this.websiteService.websiteRootInstance = undefined;
            this.websiteService.pageDocument = null;
        });

        /**
         * This removes the 'Odoo' prefix of the title service to display
         * cleanly the frontend's document title (see _replaceBrowserUrl), and
         * replaces the backend favicon with the frontend's one.
         * These changes are reverted when the component is unmounted.
         */
        useEffect(() => {
            const backendIconEl = document.querySelector("link[rel~='icon']");
            // Save initial backend values.
            const backendIconHref = backendIconEl.href;
            this.iframe.el.addEventListener('load', () => {
                // Replace backend values with frontend's ones.
                const frontendIconEl = this.iframe.el.contentDocument.querySelector("link[rel~='icon']");
                if (frontendIconEl) {
                    backendIconEl.href = frontendIconEl.href;
                }
            }, { once: true });
            return () => {
                // Restore backend initial values when leaving.
                backendIconEl.href = backendIconHref;
            };
        }, () => []);

        const toggleIsMobile = () => {
            this.iframe.el.contentDocument.documentElement
                .classList.toggle('o_is_mobile', this.websiteContext.isMobile);
        };
        // Toggle the 'o_is_mobile' class when the context 'isMobile' changes
        // (e.g. Click on mobile preview buttons).
        useEffect(toggleIsMobile, () => [this.websiteContext.isMobile]);

        // Toggle the 'o_is_mobile' class according to 'isMobile' on iframe load
        useEffect(() => {
            this.iframe.el.addEventListener('OdooFrameContentLoaded', toggleIsMobile);
            return () => this.iframe.el.removeEventListener('OdooFrameContentLoaded', toggleIsMobile);
        }, () => []);
    }

    get websiteId() {
        let websiteId = this.props.action.context.params && this.props.action.context.params.website_id;
        // When no parameter is passed to the client action, the current
        // website from the backend (which is the last viewed/edited) will be
        // taken.
        if (!websiteId) {
            websiteId = this.backendWebsiteId;
        }
        if (!websiteId) {
            websiteId = this.websiteService.websites[0].id;
        }
        return websiteId;
    }

    get websiteDomain() {
        return this.websiteService.websites.find(website => website.id === this.websiteId).domain;
    }

    get path() {
        let path = this.isRestored
            ? this.websiteService.lastUrl
            : this.props.action.context.params && this.props.action.context.params.path;

        if (path) {
            const url = new URL(path, window.location.origin);
            if (this._isTopWindowURL(url)) {
                // If the client action is initialized with a path that should
                // not be opened inside the iframe (= something we would want to
                // open on the top window), we consider that this is not a valid
                // flow. Instead of trying to open it on the top window, we
                // initialize the iframe with the website homepage...
                path = '/';
            } else {
                // ... otherwise, the path still needs to be normalized (as it
                // would be if the given path was used as an href of a  <a/>
                // element).
                path = url.pathname + url.search;
            }
        } else {
            path = '/';
        }
        return path;
    }

    get testMode() {
        return false;
    }

    get aceEditorWidth() {
        const storedWidth = browser.localStorage.getItem("ace_editor_width");
        return storedWidth ? parseInt(storedWidth) : 720;
    }

    get isMicrosoftEdge() {
        return isBrowserMicrosoftEdge();
    }

    reloadIframe(url) {
        return new Promise((resolve, reject) => {
            this.websiteService.websiteRootInstance = undefined;
            this.iframe.el.addEventListener('OdooFrameContentLoaded', resolve, { once: true });
            if (url) {
                this.iframe.el.contentWindow.location = url;
            } else {
                this.iframe.el.contentWindow.location.reload();
            }
        });
    }

    block({ showLoader = true } = {}) {
        this.blockedState.isBlocked = true;
        this.blockedState.showLoader = showLoader;
    }

    unblock() {
        this.blockedState.isBlocked = false;
        this.blockedState.showLoader = false;
    }

    addWelcomeMessage() {
        if (this.websiteService.isRestrictedEditor) {
            const wrap = this.iframe.el.contentDocument.querySelector('#wrapwrap.homepage #wrap');
            if (wrap && !wrap.innerHTML.trim()) {
                this.welcomeMessage = renderToElement('website.homepage_editor_welcome_message');
                this.welcomeMessage.classList.add('o_homepage_editor_welcome_message', 'h-100');
                while (wrap.firstChild) {
                    wrap.removeChild(wrap.lastChild);
                }
                wrap.append(this.welcomeMessage);
            }
        }
    }

    removeWelcomeMessage() {
        if (this.welcomeMessage) {
            this.welcomeMessage.remove();
        }
    }

    /**
     * Returns true if the url should be opened in the top
     * window.
     *
     * @param host {string} host of the route.
     * @param pathname {string} path of the route.
     * @private
     */
    _isTopWindowURL({ host, pathname }) {
        const backendRoutes = ['/web', '/web/session/logout', '/odoo'];
        return host !== window.location.host
            || (pathname
                && (backendRoutes.includes(pathname)
                    || pathname.startsWith('/@/')
                    || pathname.startsWith('/odoo/')
                    || pathname.startsWith('/web/content/')
                    // This is defined here to avoid creating a
                    // website_documents module for just one patch.
                    || pathname.startsWith('/document/share/')));
    }

    /**
     * This replaces the browser url (/odoo/action-website...) with
     * the iframe's url (it is clearer for the user).
     */
    _replaceBrowserUrl() {
        if (!wUtils.isHTTPSorNakedDomainRedirection(this.iframe.el.contentWindow.location.origin, window.location.origin)) {
            // If another domain ends up loading in the iframe (for example,
            // if the iframe is being redirected and has no initial URL, so it
            // loads "about:blank"), do not push that into the history
            // state as that could prevent the user from going back and could
            // trigger a traceback.
            history.replaceState(history.state, document.title, '/odoo');
            return;
        }
        const currentTitle = this.iframe.el.contentDocument.title;
        history.replaceState(history.state, currentTitle, this.iframe.el.contentDocument.location.href);
        this.title.setParts({ action: currentTitle });
    }

    _onPageLoaded(ev) {
        // FIX Chrome-only. If you have the backend in a language A but the
        // website in English only, you can 1) modify a record's (event,
        // product...) name in language A (say "New Name").
        // 2) visit the page `/new-name-11` => the server will redirect you to
        // the English page `/origin-11`, which is the only one existing.
        // Chrome caches the redirection.
        // 3) give the same name in English as in language A, try to visit
        // => the server now wants to access `/new-name-11`
        // => Chrome uses the cache to redirect `/new-name-11` to `/origin-11`,
        // => the server tries to redirect to `/new-name-11` => loop.
        // Chrome injects a "Too many redirects" layout in the iframe, which in
        // turn raises a CORS error when the app tries to update the iframe.
        // If we detect that behavior, we reload the iframe with a new query
        // parameter, so that it's not cached for Chrome.
        if (
            navigator.userAgent.toLowerCase().includes("chrome")
            && !this.iframe.el.src.includes("iframe_reload")
        ) {
            try {
                /* eslint-disable no-unused-expressions */
                this.iframe.el.contentWindow.location.href;
            } catch (err) {
                if (err.name === "SecurityError") {
                    ev.stopImmediatePropagation();
                    // Note that iframe's `src` is the URL used to start the
                    // website preview, it's not sync'd with iframe navigation.
                    const srcUrl = new URL(this.iframe.el.src);
                    const pathUrl = new URL(srcUrl.searchParams.get("path"), srcUrl.origin);
                    pathUrl.searchParams.set("iframe_reload", "1");
                    srcUrl.searchParams.set("path", `${pathUrl.pathname}${pathUrl.search}`);
                    // We could inject `pathUrl` directly but keep the same
                    // expected URL format `/website/force/1?path=..`
                    this.iframe.el.src = srcUrl.toString();
                    return;
                }
            }
        }
        if (this.lastHiddenPageURL !== this.iframe.el.contentWindow.location.href) {
            // Hide Ace Editor when moving to another page.
            this.websiteService.context.showResourceEditor = false;
            this.lastHiddenPageURL = undefined;
        }
        if (this.props.action.context.params?.with_loader) {
            this.websiteService.hideLoader();
            this.props.action.context.params.with_loader = false;
        }
        this.iframe.el.contentWindow.addEventListener('beforeunload', this._onPageUnload.bind(this));
        this._replaceBrowserUrl();
        this.iframe.el.contentWindow.addEventListener('popstate', this._replaceBrowserUrl.bind(this));
        this.iframe.el.contentWindow.addEventListener('pagehide', this._onPageHide.bind(this));

        this.websiteService.pageDocument = this.iframe.el.contentDocument;

        // This is needed for the registerThemeHomepageTour tours
        const { editable, viewXmlid } = this.websiteService.currentWebsite.metadata;
        this.container.el.dataset.viewXmlid = viewXmlid;
        // The iframefallback is hidden in test mode
        if (!editable && this.iframefallback.el) {
            this.iframefallback.el.classList.add('d-none');
        }

        this.iframe.el.contentWindow.addEventListener('PUBLIC-ROOT-READY', (event) => {
            this.iframe.el.setAttribute('is-ready', 'true');
            if (!this.websiteContext.edition && editable) {
                this.addWelcomeMessage();
            }
            this.websiteService.websiteRootInstance = event.detail.rootInstance;
        });

        // The clicks on the iframe are listened, so that links with external
        // redirections can be opened in the top window.
        this.iframe.el.contentDocument.addEventListener('click', (ev) => {
            const isEditing = this.websiteContext.edition || this.websiteContext.translation;
            if (!isEditing) {
                // Forward clicks to close backend client action's navbar
                // dropdowns.
                this.iframe.el.dispatchEvent(new MouseEvent('click', ev));
            } else {
                // When in edit mode, prevent the default behaviours of clicks
                // as to avoid DOM changes not handled by the editor.
                // (Such as clicking on a link that triggers navigating to
                // another page.)
                if (!ev.target.closest('#oe_manipulators')) {
                    ev.preventDefault();
                }
            }

            const linkEl = ev.target.closest('[href]');
            if (!linkEl) {
                return;
            }

            const { href, target, classList } = linkEl;
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
            } else if (href && target !== '_blank' && !isEditing) {
                if (this._isTopWindowURL(linkEl)) {
                    ev.preventDefault();
                    browser.location.assign(href);
                } else if (this.iframe.el.contentWindow.location.pathname !== new URL(href).pathname) {
                    // This scenario triggers a navigation inside the iframe.
                    this.websiteService.websiteRootInstance = undefined;
                }
            }
        });
        this.iframe.el.contentDocument.addEventListener('keydown', ev => {
            if (getActiveHotkey(ev) === 'control+k' && !this.websiteContext.edition) {
                // Avoid for browsers to focus on the URL bar when pressing
                // CTRL-K from within the iframe.
                ev.preventDefault();
            }
            // Check if it's a refresh first as we want to prevent default in that case.
            this._onKeydownRefresh(ev);
            this.iframe.el.dispatchEvent(new KeyboardEvent('keydown', ev));
        });
        this.iframe.el.contentDocument.addEventListener('keyup', ev => {
            this.iframe.el.dispatchEvent(new KeyboardEvent('keyup', ev));
        });
        this.iframefallback.el?.contentDocument.documentElement.replaceChildren();
    }

    /**
     * This method is called when the page is unloaded to clean
     * the iframefallback content.
     */
    _cleanIframeFallback() {
        // Remove autoplay in all iframes urls so videos are not
        // playing in the background
        const iframesEl = this.iframefallback.el.contentDocument.querySelectorAll('iframe[src]:not([src=""])');
        for (const iframeEl of iframesEl) {
            const url = new URL(iframeEl.src);
            url.searchParams.delete('autoplay');
            iframeEl.src = url.toString();
        }
    }

    _onResourceEditorResize(width) {
        browser.localStorage.setItem("ace_editor_width", width);
    }

    _onPageUnload() {
        this.iframe.el.setAttribute('is-ready', 'false');
        // Before leaving the iframe, its content is replicated on an
        // underlying iframe, to avoid for white flashes (visible on
        // Chrome Windows/Linux).
        // If the iframe is currently displaying an XML file, the body does not
        // exist, so we do not replace the iframefallback content.
        // The iframefallback is hidden in test mode
        const websiteDoc = this.iframe.el?.contentDocument;
        const fallbackDoc = this.iframefallback.el?.contentDocument;
        if (!this.websiteContext.edition && websiteDoc && fallbackDoc) {
            fallbackDoc.documentElement.replaceWith(websiteDoc.documentElement.cloneNode(true));
            this.iframefallback.el.classList.remove("d-none");
            getScrollingElement(fallbackDoc).scrollTop = getScrollingElement(websiteDoc).scrollTop;
            this._cleanIframeFallback();
        }
    }
    _onPageHide() {
        this.lastHiddenPageURL = this.iframe.el && this.iframe.el.contentWindow.location.href;
        // Normally, at this point, the websiteRootInstance is already set to
        // `undefined`, as we want to do that as early as possible to prevent
        // the editor to be in an unstable state. But some events not managed
        // by the websitePreview could trigger a `pagehide`, so for safety,
        // it is set to undefined again.
        this.websiteService.websiteRootInstance = undefined;
    }
    /**
     * Handles refreshing while the website preview is active.
     * Makes it possible to stay in the backend after an F5 or CTRL-R keypress.
     *
     * @param  {KeyboardEvent} ev
     * @private
     */
    _onKeydownRefresh(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey !== 'control+r' && hotkey !== 'f5') {
            return;
        }
        // The iframe isn't loaded yet: fallback to default refresh.
        if (this.websiteService.contentWindow === undefined) {
            return;
        }
        ev.preventDefault();
        const path = this.websiteService.contentWindow.location;
        const debugMode = this.env.debug ? `&debug=${this.env.debug}` : "";
        redirect(`/odoo/action-website.website_preview?path=${encodeURIComponent(path)}${debugMode}`);
    }
}

registry.category('actions').add('website_preview', WebsitePreview);
