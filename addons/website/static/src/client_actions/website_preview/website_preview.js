/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import core from 'web.core';
import { AceEditorAdapterComponent } from '../../components/ace_editor/ace_editor';
import { WebsiteEditorComponent } from '../../components/editor/editor';
import { WebsiteTranslator } from '../../components/translator/translator';
import {OptimizeSEODialog} from '@website/components/dialog/seo';

const { Component, onWillStart, useRef, useEffect, useState } = owl;

class BlockIframe extends Component {
    setup() {
        this.websiteService = useService('website');
        this.state = useState({
            blockIframe: false,
            showLoader: false,
        });
        this.processes = [];
        this.ANONYMOUS_PROCESS_ID = 'ANONYMOUS_PROCESS_ID';
        this.websiteService.bus.addEventListener("BLOCK", this.block.bind(this));
        this.websiteService.bus.addEventListener("UNBLOCK", this.unblock.bind(this));
    }
    block(event) {
        if (event.detail.showLoader && !this.state.showLoader) {
            setTimeout(() => {
                this.state.showLoader = true;
            }, event.detail.loaderDelay);
        }
        if (!this.processes.length) {
            this.state.blockIframe = true;
        }
        this.processes.push(event.detail.processId || this.ANONYMOUS_PROCESS_ID);
    }
    unblock(event) {
        const processId = event.detail.processId || this.ANONYMOUS_PROCESS_ID;
        const processIndex = this.processes.indexOf(processId);
        if (processIndex > -1) {
            this.processes.splice(processIndex, 1);
        }
        if (this.processes.length === 0) {
            this.state.blockIframe = false;
            this.state.showLoader = false;
        }
    }
}
BlockIframe.template = 'website.BlockIframe';

export class WebsitePreview extends Component {
    setup() {
        this.websiteService = useService('website');
        this.dialogService = useService('dialog');
        this.title = useService('title');
        this.user = useService('user');
        this.router = useService('router');
        this.action = useService('action');

        this.iframeFallbackUrl = '/website/iframefallback';

        this.iframe = useRef('iframe');
        this.iframefallback = useRef('iframefallback');
        this.container = useRef('container');
        this.websiteContext = useState(this.websiteService.context);

        onWillStart(async () => {
            await this.websiteService.fetchWebsites();
            const encodedPath = encodeURIComponent(this.path);
            if (this.websiteDomain && this.websiteDomain !== window.location.origin) {
                window.location.href = `${this.websiteDomain}/web#action=website.website_preview&path=${encodedPath}&website_id=${this.websiteId}`;
            } else {
                this.initialUrl = `/website/force/${this.websiteId}?path=${encodedPath}`;
            }
        });

        useEffect(() => {
            this.websiteService.currentWebsiteId = this.websiteId;

            // The params used to configure the context should be ignored when
            // the action is restored (example: click on the breadcrumb).
            const isRestored = this.props.action.jsId === this.websiteService.actionJsId;
            this.websiteService.actionJsId = this.props.action.jsId;
            if (isRestored) {
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

            return () => {
                this.websiteService.currentWebsiteId = null;
                this.websiteService.websiteRootInstance = undefined;
                this.websiteService.pageDocument = null;
            };
        }, () => [this.props.action.context.params]);

        useEffect(() => {
            this.websiteService.blockIframe(true, 0, 'load-iframe');
            this.iframe.el.addEventListener('load', () => this.websiteService.unblockIframe('load-iframe'), { once: true });
            // For a frontend page, it is better to use the
            // OdooFrameContentLoaded event to unblock the iframe, as it is
            // triggered faster than the load event.
            this.iframe.el.addEventListener('OdooFrameContentLoaded', () => this.websiteService.unblockIframe('load-iframe'), { once: true });
        }, () => []);
    }

    get websiteId() {
        let websiteId = this.props.action.context.params && this.props.action.context.params.website_id;
        // When no parameter is passed to the client action, the current
        // website from the website service is taken. By default, it will be
        // the one from the session.
        if (!websiteId) {
            websiteId = this.websiteService.currentWebsite && this.websiteService.currentWebsite.id;
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
        let path = this.websiteService.editedObjectPath;
        if (!path) {
            path = this.props.action.context.params && this.props.action.context.params.path;
            if (path) {
                const url = new URL(path, window.location.origin);
                if (this._isTopWindowURL(url)) {
                    // If the client action is initialized with a path that
                    // should not be opened inside the iframe (= something we
                    // would want to open on the top window), we consider that
                    // this is not a valid flow. Instead of trying to open it on
                    // the top window, we initialize the iframe with the
                    // website homepage...
                    path = '/';
                } else {
                    // ... otherwise, the path still needs to be normalized (as
                    // it would be if the given path was used as an href of a
                    // <a/> element).
                    path = url.pathname + url.search + url.hash;
                }
            } else {
                path = '/';
            }
        }
        return path;
    }

    get testMode() {
        return false;
    }

    reloadIframe(url) {
        return new Promise((resolve, reject) => {
            this.iframe.el.addEventListener('OdooFrameContentLoaded', resolve, { once: true });
            if (url) {
                this.iframe.el.contentWindow.location = url;
            } else {
                this.iframe.el.contentWindow.location.reload();
            }
        });
    }

    addWelcomeMessage() {
        if (this.websiteService.isPublisher) {
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
        return host !== window.location.host || (pathname && (backendRoutes.includes(pathname) || pathname.startsWith('/@/')));
    }

    /**
     * This replaces the browser url (/web#action=website...) with
     * the iframe's url (it is clearer for the user).
     */
    _replaceBrowserUrl() {
        const currentUrl = new URL(this.iframe.el.contentDocument.location.href);
        currentUrl.pathname = `/@${currentUrl.pathname}`;
        this.currentTitle = this.iframe.el.contentDocument.title;
        history.replaceState({}, this.currentTitle, currentUrl.href);
        this.title.setParts({ action: this.currentTitle });
    }

    _onPageLoaded() {
        this.iframe.el.contentWindow.addEventListener('beforeunload', this._onPageUnload.bind(this));
        this._replaceBrowserUrl();
        this.iframe.el.contentWindow.addEventListener('hashchange', this._replaceBrowserUrl.bind(this));

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
                            url_return: '/[lang]',
                        },
                    },
                });
            } else if (classList.contains('js_change_lang') && isEditing) {
                ev.preventDefault();
                // The switch to the right language is handled by the
                // Website Root, inside the iframe.
                this.websiteService.leaveEditMode();
            } else if (href && target !== '_blank' && !isEditing && this._isTopWindowURL(linkEl)) {
                ev.preventDefault();
                this.router.redirect(href);
            }
        });
        this.iframe.el.contentDocument.addEventListener('keydown', ev => {
            this.iframe.el.dispatchEvent(new KeyboardEvent('keydown', ev));
        });
        this.iframe.el.contentDocument.addEventListener('keyup', ev => {
            this.iframe.el.dispatchEvent(new KeyboardEvent('keyup', ev));
        });
    }

    _onPageUnload() {
        this.websiteService.websiteRootInstance = undefined;
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
}
WebsitePreview.template = 'website.WebsitePreview';
WebsitePreview.components = {
    WebsiteEditorComponent,
    BlockIframe,
    WebsiteTranslator,
    AceEditorAdapterComponent,
};

registry.category('actions').add('website_preview', WebsitePreview);
