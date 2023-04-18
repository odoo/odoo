/** @odoo-module **/

import { browser } from '@web/core/browser/browser';
import { registry } from '@web/core/registry';
import { useService, useBus } from '@web/core/utils/hooks';
import core from 'web.core';
import { AceEditorAdapterComponent } from '../../components/ace_editor/ace_editor';
import { WebsiteEditorComponent } from '../../components/editor/editor';
import { WebsiteTranslator } from '../../components/translator/translator';
import { unslugHtmlDataObject } from '../../services/website_service';
import {OptimizeSEODialog} from '@website/components/dialog/seo';
import { routeToUrl } from "@web/core/browser/router_service";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import wUtils from 'website.utils';

const { Component, onWillStart, onMounted, onWillUnmount, useRef, useEffect, useState } = owl;

class BlockPreview extends Component {}
BlockPreview.template = 'website.BlockPreview';

export class WebsitePreview extends Component {
    setup() {
        this.websiteService = useService('website');
        this.dialogService = useService('dialog');
        this.title = useService('title');
        this.user = useService('user');
        this.router = useService('router');
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

        onWillStart(async () => {
            const [backendWebsiteRepr] = await Promise.all([
                this.orm.call('website', 'get_current_website'),
                this.websiteService.fetchWebsites(),
                this.websiteService.fetchUserGroups(),
            ]);
            this.backendWebsiteId = unslugHtmlDataObject(backendWebsiteRepr).id;

            const encodedPath = encodeURIComponent(this.path);
            if (this.websiteDomain && !wUtils.isHTTPSorNakedDomainRedirection(this.websiteDomain, window.location.origin)) {
                // The website domain might be the naked one while the naked one
                // is actually redirecting to `www` (or the other way around).
                // In such a case, we need to consider those 2 from the same
                // domain and let the iframe load that "different" domain. The
                // iframe will actually redirect to the correct one (naked/www),
                // which will ends up with the same domain as the parent window
                // URL (event if it wasn't, it wouldn't be an issue as those are
                // really considered as the same domain, the user will share the
                // same session and CORS errors won't be a thing in such a case)
                window.location.href = `${encodeURI(this.websiteDomain)}/web#action=website.website_preview&path=${encodedPath}&website_id=${encodeURIComponent(this.websiteId)}`;
            } else {
                this.initialUrl = `/website/force/${encodeURIComponent(this.websiteId)}?path=${encodedPath}`;
            }
        });

        useEffect(() => {
            this.websiteService.currentWebsiteId = this.websiteId;
            if (this.isRestored) {
                return;
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

        onMounted(() => {
            this.websiteService.blockPreview(true, 'load-iframe');
            this.iframe.el.addEventListener('load', () => this.websiteService.unblockPreview('load-iframe'), { once: true });
            // For a frontend page, it is better to use the
            // OdooFrameContentLoaded event to unblock the iframe, as it is
            // triggered faster than the load event.
            this.iframe.el.addEventListener('OdooFrameContentLoaded', () => this.websiteService.unblockPreview('load-iframe'), { once: true });
        });

        onWillUnmount(() => {
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
            const { zopenerp } = this.title.getParts();
            this.iframe.el.addEventListener('load', () => {
                // Replace backend values with frontend's ones.
                this.title.setParts({ zopenerp: null });
                const frontendIconEl = this.iframe.el.contentDocument.querySelector("link[rel~='icon']");
                if (frontendIconEl) {
                    backendIconEl.href = frontendIconEl.href;
                }
            }, { once: true });
            return () => {
                // Restore backend initial values when leaving.
                this.title.setParts({ zopenerp, action: null });
                backendIconEl.href = backendIconHref;
            };
        }, () => []);

        useEffect(() => {
            let leftOnBackNavigation = false;
            // When reaching a "regular" url of the webclient's router, an
            // hashchange event should be dispatched to properly display the
            // content of the previous URL before reaching the client action,
            // which was lost after being replaced for the frontend's URL.
            const handleBackNavigation = () => {
                if (window.location.pathname === '/web') {
                    window.dispatchEvent(new HashChangeEvent('hashchange', {
                        newURL: window.location.href.toString()
                    }));
                    leftOnBackNavigation = true;
                }
            };
            window.addEventListener('popstate', handleBackNavigation);
            return () => {
                window.removeEventListener('popstate', handleBackNavigation);
                // When leaving the client action, its original url is pushed
                // so that the router can replay the action on back navigation
                // from other screens.
                if (!leftOnBackNavigation) {
                    history.pushState({}, null, this.backendUrl);
                }
            };
        }, () => []);

        const toggleIsMobile = () => {
            const wrapwrapEl = this.iframe.el.contentDocument.querySelector('#wrapwrap');
            if (wrapwrapEl) {
                wrapwrapEl.classList.toggle('o_is_mobile', this.websiteContext.isMobile);
            }
        };
        // Toggle the 'o_is_mobile' class on the wrapwrap when 'isMobile'
        // changes in the context. (e.g. Click on mobile preview buttons)
        useEffect(toggleIsMobile, () => [this.websiteContext.isMobile]);

        // Toggle the 'o_is_mobile' class on the wrapwrap according to
        // 'isMobile' on iframe load.
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
                path = url.pathname + url.search + url.hash;
            }
        } else {
            path = '/';
        }
        return path;
    }

    get testMode() {
        return false;
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
            const $wrap = $(this.iframe.el.contentDocument.querySelector('#wrapwrap.homepage')).find('#wrap');
            if ($wrap.length && $wrap.html().trim() === '') {
                this.$welcomeMessage = $(core.qweb.render('website.homepage_editor_welcome_message'));
                this.$welcomeMessage.addClass('o_homepage_editor_welcome_message');
                this.$welcomeMessage.css('min-height', $wrap.parent('main').height() - ($wrap.outerHeight(true) - $wrap.height()));
                $wrap.empty().append(this.$welcomeMessage);
            }
        }
    }

    removeWelcomeMessage() {
        if (this.$welcomeMessage) {
            this.$welcomeMessage.detach();
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
        const backendRoutes = ['/web', '/web/session/logout'];
        return host !== window.location.host
            || (pathname
                && (backendRoutes.includes(pathname)
                    || pathname.startsWith('/@/')
                    || pathname.startsWith('/web/content/')
                    // This is defined here to avoid creating a
                    // website_documents module for just one patch.
                    || pathname.startsWith('/document/share/')));
    }

    /**
     * This replaces the browser url (/web#action=website...) with
     * the iframe's url (it is clearer for the user).
     */
    _replaceBrowserUrl() {
        // The original /web#action=... url is saved to be pushed on top of the
        // history when leaving the component, so that the webclient can
        // correctly find back and replay the client action.
        if (!this.backendUrl) {
            this.backendUrl = routeToUrl(this.router.current);
        }
        const currentTitle = this.iframe.el.contentDocument.title;
        history.replaceState({}, currentTitle, this.iframe.el.contentDocument.location.href);
        this.title.setParts({ action: currentTitle });
    }

    _onPageLoaded() {
        this.iframe.el.contentWindow.addEventListener('beforeunload', this._onPageUnload.bind(this));
        this._replaceBrowserUrl();
        this.iframe.el.contentWindow.addEventListener('hashchange', this._replaceBrowserUrl.bind(this));
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
                this.action.doAction('base.action_view_base_language_install', {
                    target: 'new',
                    additionalContext: {
                        params: {
                            website_id: this.websiteId,
                            url_return: $.deparam(href).url_return,
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
            this.iframe.el.dispatchEvent(new KeyboardEvent('keydown', ev));
        });
        this.iframe.el.contentDocument.addEventListener('keyup', ev => {
            this.iframe.el.dispatchEvent(new KeyboardEvent('keyup', ev));
        });
    }

    _onPageUnload() {
        this.iframe.el.setAttribute('is-ready', 'false');
        // Before leaving the iframe, its content is replicated on an
        // underlying iframe, to avoid for white flashes (visible on
        // Chrome Windows/Linux).
        // If the iframe is currently displaying an XML file, the body does not
        // exist, so we do not replace the iframefallback content.
        // The iframefallback is hidden in test mode
        if (!this.websiteContext.edition && this.iframe.el.contentDocument.body && this.iframefallback.el) {
            this.iframefallback.el.contentDocument.body.replaceWith(this.iframe.el.contentDocument.body.cloneNode(true));
            this.iframefallback.el.classList.remove('d-none');
            $().getScrollingElement(this.iframefallback.el.contentDocument)[0].scrollTop = $().getScrollingElement(this.iframe.el.contentDocument)[0].scrollTop;
        }
    }
    _onPageHide() {
        // Normally, at this point, the websiteRootInstance is already set to
        // `undefined`, as we want to do that as early as possible to prevent
        // the editor to be in an unstable state. But some events not managed
        // by the websitePreview could trigger a `pagehide`, so for safety,
        // it is set to undefined again.
        this.websiteService.websiteRootInstance = undefined;
    }
}
WebsitePreview.template = 'website.WebsitePreview';
WebsitePreview.components = {
    WebsiteEditorComponent,
    BlockPreview,
    WebsiteTranslator,
    AceEditorAdapterComponent,
};

registry.category('actions').add('website_preview', WebsitePreview);
