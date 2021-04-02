/** @odoo-module **/

import Widget from 'web.Widget';
import {_t} from 'web.core';
import {DropPrevious} from 'web.concurrency';

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
     */
    init(parent, target) {
        this._super(...arguments);
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
        this.$('[data-toggle="tooltip"]').tooltip({delay: 0, placement: 'bottom'});
        this.$target.popover({
            html: true,
            content: this.$el,
            placement: 'bottom',
            trigger: 'click',
        })
        .on('show.bs.popover.link_popover', () => {
            this._loadAsyncLinkPreview();
        })
        .popover('show')
        .data('bs.popover').tip.classList.add('o_edit_menu_popover');

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
        this.$target.popover('dispose');
        return this._super(...arguments);
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
        try {
            url = new URL(this.target.href); // relative to absolute
        } catch (e) {
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
        this.$previewFaviconFa.removeClass('d-none').addClass('fa-globe');
        this.$urlLink.text(url).attr('href', url);
        this.$fullUrl.text(url).addClass('d-none').removeClass('o_we_webkit_box');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Opens the Link Dialog.
     *
     * TODO Call business methods once new editor is released instead of click
     *
     * @private
     * @param {Event} ev
     */
    _onEditLinkClick(ev) {
        $('.note-link-popover [data-event="showLinkDialog"]').click();
    },
    /**
     * Removes the link/anchor.
     *
     * TODO Call business methods once new editor is released instead of click
     *
     * @private
     * @param {Event} ev
     */
    _onRemoveLinkClick(ev) {
        $('.note-link-popover [data-event="unlink"]').click();
    },
});

LinkPopoverWidget.createFor = async function (parent, targetEl) {
    // Target might already have a popover, eg cart icon in navbar
    if ($(targetEl).data('bs.popover')) {
        return null;
    }
    const popoverWidget = new this(parent, targetEl);
    return popoverWidget.appendTo(targetEl).then(() => popoverWidget);
};

export default LinkPopoverWidget;
