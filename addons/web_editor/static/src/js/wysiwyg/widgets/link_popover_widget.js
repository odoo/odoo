/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ancestors } from '@web_editor/js/common/wysiwyg_utils';
import { KeepLast } from '@web/core/utils/concurrency';
import { browser } from "@web/core/browser/browser";

export class LinkPopoverWidget {
    static createFor(params) {
        const noLinkPopoverClass = ".o_no_link_popover, .carousel-control-prev, .carousel-control-next, .dropdown-toggle";
        // Target might already have a popover, eg cart icon in navbar
        const alreadyPopover = $(params.target).data('bs.popover');
        if (alreadyPopover || $(params.target).is(noLinkPopoverClass) || !!$(params.target).parents(noLinkPopoverClass).length) {
            return null;
        }
        const popoverWidget = new this(params);
        params.wysiwyg?.odooEditor.observerUnactive('LinkPopoverWidget');
        popoverWidget.start(); // This is not async
        params.wysiwyg?.odooEditor.observerActive('LinkPopoverWidget');
        return popoverWidget;
    };

    template = `
        <div class="d-flex">
            <span class="me-2 o_we_preview_favicon"><i class="fa fa-globe"></i><img class="align-baseline d-none"></img></span>
            <div class="w-100">
                <div class="d-flex">
                    <a href="#" target="_blank" class="o_we_url_link fw-bold flex-grow-1 text-truncate" title="${_t('Open in a new tab')}"></a>
                    <a href="#" class="mx-1 o_we_copy_link text-dark" data-bs-toggle="tooltip" data-bs-placement="top" title="${_t('Copy Link')}">
                        <i class="fa fa-clone"></i>
                    </a>
                    <a href="#" class="mx-1 o_we_edit_link text-dark" data-bs-toggle="tooltip" data-bs-placement="top" title="${_t('Edit Link')}">
                        <i class="fa fa-edit"></i>
                    </a>
                    <a href="#" class="ms-1 o_we_remove_link text-dark" data-bs-toggle="tooltip" data-bs-placement="top" title="${_t('Remove Link')}">
                        <i class="fa fa-chain-broken"></i>
                    </a>
                </div>
                <a href="#" target="_blank" class="o_we_full_url mt-1 text-muted d-none" title="${_t('Open in a new tab')}"></a>
            </div>
        </div>
    `;

    constructor(params) {
        const template = document.createElement('template');
        template.innerHTML = this.template;
        this.el = template.content.firstElementChild;
        this.$el = $(this.el);

        this.wysiwyg = params.wysiwyg;
        this.target = params.target;
        this.notify = params.notify;
        this.$target = $(params.target);
        this.container = params.container || this.target.ownerDocument.body;
        this.href = this.$target.attr('href'); // for template
        this._keepLastPromise = new KeepLast();
    }

    /**
     *
     * @override
     */
    start() {
        this.$urlLink = this.$el.find('.o_we_url_link');
        this.$previewFaviconImg = this.$el.find('.o_we_preview_favicon img');
        this.$previewFaviconFa = this.$el.find('.o_we_preview_favicon .fa');
        this.$copyLink = this.$el.find('.o_we_copy_link');
        this.$fullUrl = this.$el.find('.o_we_full_url');

        this.$urlLink.attr('href', this.href);
        this.$fullUrl.attr('href', this.href);
        this.$el.find(`.o_we_edit_link`).on('click', this._onEditLinkClick.bind(this));
        this.$el.find(`.o_we_remove_link`).on('click', this._onRemoveLinkClick.bind(this));

        this.$copyLink.on("click", this._onCopyLinkClick.bind(this));

        // init tooltips & popovers
        this.$el.find('[data-bs-toggle="tooltip"]').tooltip({
            delay: 0,
            placement: 'bottom',
            container: this.container,
        });
        const tooltips = [];
        for (const el of this.$el.find('[data-bs-toggle="tooltip"]').toArray()) {
            tooltips.push(Tooltip.getOrCreateInstance(el));
        }
        let popoverShown = true;
        const editable = this.wysiwyg.odooEditor.editable;
        this.$target.popover({
            html: true,
            content: this.$el,
            placement: 'bottom',
            // We need the popover to:
            // 1. Open when the link is clicked or double clicked
            // 2. Remain open when the link is clicked again (which `trigger: 'click'` is not doing)
            // 3. Remain open when the popover content is clicked..
            // 4. ..except if it the click was on a button of the popover content
            // 5. Close when the user click somewhere on the page (not being the link or the popover content)
            trigger: 'manual',
            boundary: editable,
            container: this.container,
        })
        .on('show.bs.popover.link_popover', () => {
            this._loadAsyncLinkPreview();
            popoverShown = true;
        })
        .on('hide.bs.popover.link_popover', () => {
            popoverShown = false;
        })
        .on('hidden.bs.popover.link_popover', () => {
            for (const tooltip of tooltips) {
                tooltip.hide();
            }
        })
        .on('inserted.bs.popover.link_popover', () => {
            const popover = Popover.getInstance(this.target);
            popover.tip.classList.add('o_edit_menu_popover');
        })
        .popover('show');

        this.popover = Popover.getInstance(this.target);
        this.$target.on('mousedown.link_popover', (e) => {
            if (!popoverShown) {
                this.$target.popover('show');
            }
        });
        this.$target.on('href_changed.link_popover', (e) => {
            // Do not change shown/hidden state.
            if (popoverShown) {
                this._loadAsyncLinkPreview();
            }
        });
        const onClickDocument = (e) => {
            if (popoverShown) {
                const hierarchy = [e.target, ...ancestors(e.target)];
                if (
                    !(
                        hierarchy.includes(this.$target[0]) ||
                        (hierarchy.includes(this.$el[0]) &&
                            !hierarchy.some(x => x.tagName && x.tagName === 'A' && (x === this.$urlLink[0] || x === this.$fullUrl[0])))
                    )
                ) {
                    // Note: For buttons of the popover, their listeners should
                    // handle the hide themselves to avoid race conditions.
                    this.popover.hide();
                }
            }
        };
        $(document).on('mouseup.link_popover', onClickDocument);
        if (document !== this.wysiwyg.odooEditor.document) {
            $(this.wysiwyg.odooEditor.document).on('mouseup.link_popover', onClickDocument);
        }

        // Update popover's content and position upon changes
        // on the link's label or href.
        this._observer = new MutationObserver(records => {
            if (!popoverShown) {
                return;
            }
            if (records.some(record => record.type === 'attributes')) {
                this._loadAsyncLinkPreview();
            }
            this.$target.popover('update');
        });
        this._observer.observe(this.target, {
            subtree: true,
            characterData: true,
            attributes: true,
            attributeFilter: ['href'],
        });
    }
    /**
     *
     * @override
     */
    destroy() {
        // FIXME those are never destroyed, so this could be a cause of memory
        // leak. However, it is only one leak per click on a link during edit
        // mode so this should not be a huge problem.
        this.$target.off('.link_popover');
        $(document).off('.link_popover');
        $(this.wysiwyg.odooEditor.document).off('.link_popover');
        this.$target.popover('dispose');
        this._observer.disconnect();
    }

    /**
     *  Hide the popover.
     */
    hide() {
        this.$target.popover('hide');
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetches and gets the link preview data (title, description..).
     * For external URL, only the favicon will be loaded.
     *
     * @private
     */
    async _loadAsyncLinkPreview() {
        let url;
        if (this.target.href === '') {
            this._resetPreview('');
            this.$previewFaviconFa.removeClass('fa-globe').addClass('fa-question-circle-o');
            return;
        }
        try {
            url = new URL(this.target.href); // relative to absolute
        } catch {
            // Invalid URL, might happen with editor unsuported protocol. eg type
            // `geo:37.786971,-122.399677`, become `http://geo:37.786971,-122.399677`
            this.notify(_t("This URL is invalid. Preview couldn't be updated."), {
                type: 'danger',
            });
            return;
        }

        this._resetPreview(url);
        const protocol = url.protocol;
        if (!protocol.startsWith('http')) {
            const faMap = {'mailto:': 'fa-envelope-o', 'tel:': 'fa-phone'};
            const icon = faMap[protocol];
            if (icon) {
                this.$previewFaviconFa.toggleClass(`fa-globe ${icon}`);
            }
        } else if (window.location.hostname !== url.hostname) {
            // Preview pages from current website only. External website will
            // most of the time raise a CORS error. To avoid that error, we
            // would need to fetch the page through the server (s2s), involving
            // enduser fetching problematic pages such as illicit content.
            this.$previewFaviconImg.attr({
                'src': `https://www.google.com/s2/favicons?sz=16&domain=${encodeURIComponent(url)}`
            }).removeClass('d-none');
            this.$previewFaviconFa.addClass('d-none');
        } else {
            await this._keepLastPromise.add($.get(this.target.href)).then(content => {
                const parser = new window.DOMParser();
                const doc = parser.parseFromString(content, "text/html");

                // Get
                const favicon = doc.querySelector("link[rel~='icon']");
                const ogTitle = doc.querySelector("[property='og:title']");
                const title = doc.querySelector("title");

                // Set
                if (favicon) {
                    this.$previewFaviconImg.attr({'src': favicon.href}).removeClass('d-none');
                    this.$previewFaviconFa.addClass('d-none');
                }
                if (ogTitle || title) {
                    this.$urlLink.text(ogTitle ? ogTitle.getAttribute('content') : title.text.trim());
                }
                this.$fullUrl.removeClass('d-none').addClass('o_we_webkit_box');
            }).catch(error => {
                // HTML error codes should not prevent to edit the links, so we
                // only check for proper instances of Error.
                if (error instanceof Error) {
                    return Promise.reject(error);
                }
            }).finally(() => {
                this.$target.popover('update');
            });
        }
    }
    /**
     * Resets the preview elements visibility. Particularly useful when changing
     * the link url from an internal to an external one and vice versa.
     *
     * @private
     * @param {string} url
     */
    _resetPreview(url) {
        this.$previewFaviconImg.addClass('d-none');
        this.$previewFaviconFa.removeClass('d-none fa-question-circle-o fa-envelope-o fa-phone').addClass('fa-globe');
        this.$urlLink.add(this.$fullUrl).text(url || _t('No URL specified')).attr('href', url || null);
        this.$fullUrl.addClass('d-none').removeClass('o_we_webkit_box');
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens the Link Dialog.
     *
     * TODO The editor instance should be reached a proper way
     *
     * @private
     * @param {Event} ev
     */
    _onEditLinkClick(ev) {
        ev.preventDefault();
        this.wysiwyg.toggleLinkTools({
            forceOpen: true,
            link: this.$target[0],
        });
        ev.stopImmediatePropagation();
        this.popover.hide();
    }
    /**
     * Removes the link/anchor.
     *
     * @private
     * @param {Event} ev
     */
    _onRemoveLinkClick(ev) {
        ev.preventDefault();
        this.wysiwyg.removeLink();
        ev.stopImmediatePropagation();
        this.popover.hide();
    }
    /**
     * Copy the link/anchor
     * 
     * @private
     * @param {Event} ev
     */
    async _onCopyLinkClick(ev) {
        ev.preventDefault();
        await browser.navigator.clipboard.writeText(this.target.href);
        this.$copyLink.tooltip('hide');
        this.notify(_t("Link copied to clipboard."), {
            type: 'success',
        });
        this.popover.hide();
    }
}
