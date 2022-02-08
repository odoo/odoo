/** @odoo-module **/

import FormView from 'web.FormView';
import FormController from 'web.FormController';
import FormRenderer from 'web.FormRenderer';
import { bus, _t } from 'web.core';
import viewRegistry from 'web.view_registry';
import config from 'web.config';

const MassMailingFullWidthFormController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events,{
        iframe_updated: '_onIframeUpdated',
    }),

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        bus.on('DOM_updated', this, this._onDomUpdated);
        this._resizeObserver =  new ResizeObserver(entries => {
            // We wrap this in requestAnimationFrame to greatly mitigate
            // the "ResizeObserver loop limit exceeded" error.
            window.requestAnimationFrame(() => {
                if (!Array.isArray(entries) || !entries.length) {
                    return;
                }
                this._onResizeIframeContents(entries);
            });
        });
    },
    /**
     * @override
     */
    destroy() {
        bus.off('DOM_updated', this, this._onDomUpdated);
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Resize the mailing editor's iframe container so its height fits its
     * contents. This needs to be called whenever the iframe's contents might
     * have changed, eg. when adding/removing content to/from it or when a
     * template is picked.
     *
     * @private
     */
    _resizeMailingEditorIframe() {
        const VERTICAL_OFFSET = 12; // Vertical offset picked for visual design purposes.
        const minHeight = $(window).height() - Math.abs(this.$iframe.offset().top) - (VERTICAL_OFFSET / 2);
        const $iframeDoc = this.$iframe.contents();
        const $themeSelectorNew = $iframeDoc.find('.o_mail_theme_selector_new');
        if ($themeSelectorNew.length) {
            this.$iframe.height(Math.max($themeSelectorNew[0].scrollHeight + VERTICAL_OFFSET, minHeight));
        } else {
            const ref = $iframeDoc.find('#iframe_target')[0];
            if (ref) {
                this.$iframe.height(Math.max(ref.scrollHeight + VERTICAL_OFFSET, minHeight));
            }
        }
    },
    /**
     * Reposition the sidebar so it always occupies the full available visible
     * height, no matter the scroll position. This way, the sidebar is always
     * visible and as big as possible.
     *
     * @private
     */
    _repositionMailingEditorSidebar() {
        const windowHeight = $(window).height();
        const $iframeDocument = this.$iframe.contents();
        const $sidebar = $iframeDocument.find('#oe_snippets');
        const isFullscreen =  this._isFullScreen();
        if (isFullscreen) {
            $sidebar.height(windowHeight);
            this.$iframe.height(windowHeight);
            $sidebar.css({
                top: '',
                bottom: '',
            });
        } else {
            const iframeTop = this.$iframe.offset().top;
            $sidebar.css({
                height: '',
                top: Math.max(0, this.$('.o_content').offset().top - iframeTop),
                bottom: this.$iframe.height() - windowHeight + iframeTop,
            });
        }
    },
    /**
     * Return true if the mailing editor is in full screen mode, false
     * otherwise.
     *
     * @private
     * @returns {boolean}
     */
    _isFullScreen() {
        return window.top.document.body.classList.contains('o_field_widgetTextHtml_fullscreen');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Assume the iframe was updated on each dom_updated event.
     *
     * @private
     */
    _onDomUpdated() {
        const data = { $iframe: this.$('iframe.wysiwyg_iframe:visible, iframe.o_readonly:visible') };
        this._onIframeUpdated({ data });
    },
    /**
     * Resize the given iframe so its height fits its contents and initialize a
     * resize observer to resize on each size change in its contents.
     * This also ensures the contents of the sidebar remain visible no matter
     * how much we resize the iframe and scroll down.
     *
     * @private
     * @param {JQuery} ev.data.$iframe
     */
    _onIframeUpdated(ev) {
        const $iframe = ev.data.$iframe;
        if (!$iframe.length || !$iframe.contents().length) {
            return;
        }
        const hasIframeChanged = $iframe !== this.$iframe;
        this.$iframe = $iframe;
        this._resizeMailingEditorIframe();

        const $iframeDoc = $iframe.contents();
        const iframeTarget = $iframeDoc.find('#iframe_target');
        if (hasIframeChanged) {
            $iframeDoc.find('body').on('click', '.o_fullscreen_btn', this._onToggleFullscreen.bind(this));
            this.$('.o_content').on('scroll', this._repositionMailingEditorSidebar.bind(this));
            if (iframeTarget[0]) {
                this._resizeObserver.disconnect();
                this._resizeObserver.observe(iframeTarget[0]);
            }
        }
        if (iframeTarget[0]) {
            const isFullscreen = this._isFullScreen();
            iframeTarget.css({
                display: isFullscreen ? '' : 'flex',
                'flex-direction': isFullscreen ? '' : 'column',
            });
        }
    },
    /**
     * Switch "scrolling modes" on toggle fullscreen mode: in fullscreen mode,
     * the scroll happens within the iframe whereas in regular mode we pretend
     * there is no iframe and scroll in the top document. Also reposition the
     * sidebar since toggling the fullscreen mode visibly changes the
     * positioning of elements in the document.
     *
     * @private
     */
    _onToggleFullscreen() {
        const $iframeDoc = this.$iframe.contents();
        const iframeTarget = $iframeDoc.find('#iframe_target');
        const isFullscreen = this._isFullScreen();
        iframeTarget.css({
            display: isFullscreen ? '' : 'flex',
            'flex-direction': isFullscreen ? '' : 'column',
        });
        const wysiwyg = $iframeDoc.find('.note-editable').data('wysiwyg');
        if (wysiwyg && wysiwyg.snippetsMenu) {
            // Restore the appropriate scrollable depending on the mode.
            this._$scrollable = this._$scrollable || wysiwyg.snippetsMenu.$scrollable;
            wysiwyg.snippetsMenu.$scrollable = isFullscreen ? $iframeDoc.find('.note-editable') : this._$scrollable;
        }
        this._repositionMailingEditorSidebar();
    },
    /**
     * Resize the iframe and reposition the sidebar whenever the contents of the
     * iframe change height.
     *
     * @private
     */
    _onResizeIframeContents() {
        this._resizeMailingEditorIframe();
        this._repositionMailingEditorSidebar();
    },
});

const MassMailingFullWidthFormRenderer = FormRenderer.extend({
    /**
     * Overload the rendering of the header in order to add a child to it: move
     * the alert after the statusbar.
     *
     * @private
     * @override
     */
    _renderTagHeader: function (node) {
        const $statusbar = this._super(...arguments);
        const alert = node.children.find(child => child.tag === "div" && child.attrs.role === "alert");
        const $alert = this._renderGenericTag(alert);
        $statusbar.find('.o_statusbar_buttons').after($alert);
        return $statusbar;
    },
    /**
     * Increase the default number of button boxes before folding since the form
     * without sheet is a lot bigger and more space is available for them.
     *
     * @private
     * @override
     */
    _renderButtonBoxNbButtons: function () {
        return [2, 2, 2, 4, 6, 7][config.device.size_class] || 10;
    },
});

export const MassMailingFullWidthFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Controller: MassMailingFullWidthFormController,
        Renderer: MassMailingFullWidthFormRenderer,
    }),
});

viewRegistry.add('mailing_mailing_view_form_full_width', MassMailingFullWidthFormView);
