/** @odoo-module **/

import Widget from 'web.Widget';
import {_t} from 'web.core';
import {DropPrevious} from 'web.concurrency';
import { ancestors } from '@web_editor/js/common/wysiwyg_utils';

const LinkPopoverWidget = Widget.extend({
    template: 'wysiwyg.widgets.link.edit.tooltip',
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],
    events: {
        'click .o_we_remove_link': '_onRemoveLinkClick',
        'click .o_we_edit_link': '_onEditLinkClick',
    },

    /**
     * @constructor
     * @param {Element} target: target Element for which we display a popover
     * @param {Wysiwyg} [option.wysiwyg]: The wysiwyg editor
     */
    init(parent, target, options) {
        this._super(...arguments);
        this.options = options;
        this.target = target;
        this.$target = $(target);
        this.href = this.$target.attr('href'); // for template
        this._dp = new DropPrevious();
    },
    /**
     *
     * @override
     */
    start() {
        this.$urlLink = this.$('.o_we_url_link');
        this.$previewFaviconImg = this.$('.o_we_preview_favicon img');
        this.$previewFaviconFa = this.$('.o_we_preview_favicon .fa');
        this.$copyLink = this.$('.o_we_copy_link');
        this.$fullUrl = this.$('.o_we_full_url');

        // Copy onclick handler
        const clipboard = new ClipboardJS(
            this.$copyLink[0],
            {text: () => this.target.href} // Absolute href
        );
        clipboard.on('success', () => {
            this.$copyLink.tooltip('hide');
            this.displayNotification({
                type: 'success',
                message: _t("Link copied to clipboard."),
            });
        });

        // init tooltips & popovers
        this.$('[data-toggle="tooltip"]').tooltip({
            delay: 0,
            placement: 'bottom',
            container: this.options.wysiwyg.odooEditor.document.body,
        });
        const tooltips = [];
        for (const el of this.$('[data-toggle="tooltip"]').toArray()) {
            tooltips.push($(el).data('bs.tooltip'));
        }
        let popoverShown = true;
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
            boundary: 'viewport',
            container: this.options.wysiwyg.odooEditor.document.body,
        })
        .on('show.bs.popover.link_popover', () => {
            this.options.wysiwyg.odooEditor.observerUnactive('show.bs.popover');
            this._loadAsyncLinkPreview();
            popoverShown = true;
        })
        .on('inserted.bs.popover', () => {
            this.options.wysiwyg.odooEditor.observerActive('show.bs.popover');
        })
        .on('hide.bs.popover.link_popover', () => {
            this.options.wysiwyg.odooEditor.observerUnactive('hide.bs.popover');
            popoverShown = false;
        })
        .on('hidden.bs.popover.link_popover', () => {
            this.options.wysiwyg.odooEditor.observerActive('hide.bs.popover');
            for (const tooltip of tooltips) {
                tooltip.hide();
            }
        })
        .on('inserted.bs.popover.link_popover', () => {
            this.$target.data('bs.popover').tip.classList.add('o_edit_menu_popover');
        })
        .popover('show');


        this.popover = this.$target.data('bs.popover');
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
                            !hierarchy.some(x => x.tagName && x.tagName === 'A'))
                    )
                ) {
                    this.popover.hide();
                }
            }
        }
        $(document).on('mouseup.link_popover', onClickDocument);
        if (document !== this.options.wysiwyg.odooEditor.document) {
            $(this.options.wysiwyg.odooEditor.document).on('mouseup.link_popover', onClickDocument);
        }

        return this._super(...arguments);
    },
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
        $(this.options.wysiwyg.odooEditor.document).off('.link_popover');
        this.$target.popover('dispose');
        return this._super(...arguments);
    },

    /**
     *  Hide the popover.
     */
    hide() {
        this.$target.popover('hide');
    },

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
        } catch (_e) {
            // Invalid URL, might happen with editor unsuported protocol. eg type
            // `geo:37.786971,-122.399677`, become `http://geo:37.786971,-122.399677`
            this.displayNotification({
                type: 'danger',
                message: _t("This URL is invalid. Preview couldn't be updated."),
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
                'src': `https://www.google.com/s2/favicons?sz=16&domain=${url}`
            }).removeClass('d-none');
            this.$previewFaviconFa.addClass('d-none');
        } else {
            await this._dp.add($.get(this.target.href)).then(content => {
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
                this.$target.popover('update');
            });
        }
    },
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
        this.$urlLink.text(url || _t('No URL specified')).attr('href', url || null);
        this.$fullUrl.text(url).addClass('d-none').removeClass('o_we_webkit_box');
    },

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
        this.options.wysiwyg.toggleLinkTools({
            forceOpen: true,
            link: this.$target[0],
        });
        ev.stopImmediatePropagation();
    },
    /**
     * Removes the link/anchor.
     *
     * @private
     * @param {Event} ev
     */
    _onRemoveLinkClick(ev) {
        ev.preventDefault();
        this.options.wysiwyg.removeLink();
        ev.stopImmediatePropagation();
    },
});

LinkPopoverWidget.createFor = async function (parent, targetEl, options) {
    const noLinkPopoverClass = ".o_no_link_popover, .carousel-control-prev, .carousel-control-next, .dropdown-toggle";
    // Target might already have a popover, eg cart icon in navbar
    const alreadyPopover = $(targetEl).data('bs.popover');
    if (alreadyPopover || $(targetEl).is(noLinkPopoverClass) || !!$(targetEl).parents(noLinkPopoverClass).length) {
        return null;
    }
    const popoverWidget = new this(parent, targetEl, options);
    const wysiwyg = $('#wrapwrap').data('wysiwyg');
    if (wysiwyg) {
        wysiwyg.odooEditor.observerUnactive('LinkPopoverWidget');
    }
    await popoverWidget.appendTo(targetEl)
    if (wysiwyg) {
        wysiwyg.odooEditor.observerActive('LinkPopoverWidget');
    }
    return popoverWidget;
};

export default LinkPopoverWidget;
