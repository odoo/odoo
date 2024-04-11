odoo.define('website.s_popup', function (require) {
'use strict';

const config = require('web.config');
const { _t } = require("@web/core/l10n/translation");
const dom = require('web.dom');
const publicWidget = require('web.public.widget');
const utils = require('web.utils');
const { cloneContentEls } = require("website.utils");

// TODO In master, export this class too or merge it with PopupWidget
const SharedPopupWidget = publicWidget.Widget.extend({
    selector: '.s_popup',
    disabledInEditableMode: false,
    events: {
        // A popup element is composed of a `.s_popup` parent containing the
        // actual `.modal` BS modal. Our internal logic and events are hiding
        // and showing this inner `.modal` modal element without considering its
        // `.s_popup` parent. It means that when the `.modal` is hidden, its
        // `.s_popup` parent is not touched and kept visible.
        // It might look like it's not an issue as it would just be an empty
        // element (its only child is hidden) but it leads to some issues as for
        // instance on chrome this div will have a forced `height` due to its
        // `contenteditable=true` attribute in edit mode. It will result in a
        // ugly white bar.
        // tl;dr: this is keeping those 2 elements visibility synchronized.
        'show.bs.modal': '_onModalShow',
        'hidden.bs.modal': '_onModalHidden',
    },

    /**
     * @override
     */
    destroy() {
        this._super(...arguments);

        if (!this._isNormalCase()) {
            return;
        }

        // Popup are always closed when entering edit mode (see PopupWidget),
        // this allows to make sure the class is sync on the .s_popup parent
        // after that moment too.
        if (!this.editableMode) {
            this.el.classList.add('d-none');
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This whole widget was added as a stable fix, this function allows to
     * be a bit more stable friendly. TODO remove in master.
     */
    _isNormalCase() {
        return this.el.children.length === 1
            && this.el.firstElementChild.classList.contains('modal');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onModalShow() {
        if (!this._isNormalCase()) {
            return;
        }
        this.el.classList.remove('d-none');
    },
    /**
     * @private
     */
    _onModalHidden() {
        if (!this._isNormalCase()) {
            return;
        }
        if (this.el.querySelector('.s_popup_no_backdrop')) {
            // We trigger a scroll event here to call the
            // '_hideBottomFixedElements' method and re-display any bottom fixed
            // elements that may have been hidden (e.g. the live chat button
            // hidden when the cookies bar is open).
            $().getScrollingTarget()[0].dispatchEvent(new Event('scroll'));
        }
        this.el.classList.add('d-none');
    },
});

publicWidget.registry.SharedPopup = SharedPopupWidget;

const PopupWidget = publicWidget.Widget.extend({
    selector: ".s_popup:not(#website_cookies_bar)",
    events: {
        'click .js_close_popup': '_onCloseClick',
        'hide.bs.modal': '_onHideModal',
        'show.bs.modal': '_onShowModal',
    },

    /**
     * @override
     */
    start: function () {
        this._popupAlreadyShown = !!utils.get_cookie(this.$el.attr('id'));
        if (!this._popupAlreadyShown) {
            this._bindPopup();
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        $(document).off('mouseleave.open_popup');
        this.$target.find('.modal').modal('hide');
        clearTimeout(this.timeout);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _bindPopup: function () {
        const $main = this.$target.find('.modal');

        let display = $main.data('display');
        let delay = $main.data('showAfter');

        if (config.device.isMobile) {
            if (display === 'mouseExit') {
                display = 'afterDelay';
                delay = 5000;
            }
            this.$('.modal').removeClass('s_popup_middle').addClass('s_popup_bottom');
        }

        if (display === 'afterDelay') {
            this.timeout = setTimeout(() => this._showPopup(), delay);
        } else {
            $(document).on('mouseleave.open_popup', () => this._showPopup());
        }
    },
    /**
     * @private
     */
    _canShowPopup() {
        return true;
    },
    /**
     * @private
     */
    _hidePopup: function () {
        this.$target.find('.modal').modal('hide');
    },
    /**
     * @private
     */
    _showPopup: function () {
        if (this._popupAlreadyShown || !this._canShowPopup()) {
            return;
        }
        this.$target.find('.modal').modal('show');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCloseClick: function () {
        this._hidePopup();
    },
    /**
     * @private
     */
    _onHideModal: function () {
        const nbDays = this.$el.find('.modal').data('consentsDuration');
        utils.set_cookie(this.$el.attr('id'), true, nbDays * 24 * 60 * 60);
        this._popupAlreadyShown = true;

        this.$target.find('.media_iframe_video iframe').each((i, iframe) => {
            iframe.src = '';
        });
    },
    /**
     * @private
     */
    _onShowModal() {
        this.el.querySelectorAll('.media_iframe_video').forEach(media => {
            const iframe = media.querySelector('iframe');
            iframe.src = media.dataset.oeExpression || media.dataset.src; // TODO still oeExpression to remove someday
        });
    },
});

publicWidget.registry.popup = PopupWidget;

publicWidget.registry.cookies_bar = PopupWidget.extend({
    selector: "#website_cookies_bar",

    /**
     * @override
     */
    start() {
        const policyLinkEl = this.el.querySelector(".o_cookies_bar_text_policy");
        if (policyLinkEl && window.location.pathname === new URL(policyLinkEl.href).pathname) {
            this.toggleEl = cloneContentEls(`
            <button class="o_cookies_bar_toggle btn btn-info btn-sm rounded-circle d-flex align-items-center justify-content-center position-absolute">
                <i class="fa fa-eye" alt="" aria-hidden="true"></i> <span class="o_cookies_bar_toggle_label"></span>
            </button>
            `).firstElementChild;
            this._onToggleCookiesBar = this._toggleCookiesBar.bind(this);
            this.toggleEl.addEventListener("click", this._onToggleCookiesBar);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        if (this.toggleEl) {
            this.toggleEl.removeEventListener("click", this._onToggleCookiesBar);
            this.toggleEl.remove();
        }
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _showPopup() {
        this._super(...arguments);
        if (this.toggleEl) {
            this._toggleCookiesBar();
        }
    },
    /**
     * Toggles the cookies bar with a button so that the page is readable.
     *
     * @private
     */
    _toggleCookiesBar() {
        const popupEl = this.el.querySelector(".modal");
        $(popupEl).modal("toggle");
        // As we're using Bootstrap's events, the PopupWidget prevents the modal
        // from being shown after hiding it: override that behavior.
        this._popupAlreadyShown = false;
        utils.set_cookie(this.el.id, false, -1);

        const hidden = !popupEl.classList.contains("show");
        // Keep a margin with the bottom of the page (if the modal is hidden) or
        // with the modal (if it is shown).
        const insetBlock = hidden ? "1rem" : `calc(-1*(${this.toggleEl.offsetHeight}px + .5rem))`;
        (hidden ? document.body : this.el.querySelector(".modal-content"))
            .appendChild(this.toggleEl);
        this.toggleEl.querySelector(".fa").className = `fa ${hidden ? "fa-eye" : "fa-eye-slash"}`;
        this.toggleEl.querySelector(".o_cookies_bar_toggle_label").innerText = hidden
            ? _t("Show the cookies bar")
            : _t("Hide the cookies bar");
        this.toggleEl.style.insetInlineEnd = hidden || this.el.querySelector(".s_popup_size_full")
            ? "1rem"
            : "0";
        this.toggleEl.style.insetBlock = !hidden && popupEl.classList.contains("s_popup_bottom")
            ? `${insetBlock} auto`
            : `auto ${insetBlock}`;
    },
});

// Try to update the scrollbar based on the current context (modal state)
// and only if the modal overflowing has changed

function _updateScrollbar(ev) {
    const context = ev.data;
    const isOverflowing = dom.hasScrollableContent(context._element);
    if (context._isOverflowingWindow !== isOverflowing) {
        context._isOverflowingWindow = isOverflowing;
        context._checkScrollbar();
        context._setScrollbar();
        if (isOverflowing) {
            document.body.classList.add('modal-open');
        } else {
            document.body.classList.remove('modal-open');
            context._resetScrollbar();
        }
    }
}

// Prevent bootstrap to prevent scrolling and to add the strange body
// padding-right they add if the popup does not use a backdrop (especially
// important for default cookie bar).

const _baseShowElement = $.fn.modal.Constructor.prototype._showElement;
$.fn.modal.Constructor.prototype._showElement = function () {
    _baseShowElement.apply(this, arguments);

    if (this._element.classList.contains('s_popup_no_backdrop')) {
        // Update the scrollbar if the content changes or if the window has been
        // resized. Note this could technically be done for all modals and not
        // only the ones with the s_popup_no_backdrop class but that would be
        // useless as allowing content scroll while a modal with that class is
        // opened is a very specific Odoo behavior.
        $(this._element).on('content_changed.update_scrollbar', this, _updateScrollbar);
        $(window).on('resize.update_scrollbar', this, _updateScrollbar);

        this._odooLoadEventCaptureHandler = _.debounce(() => _updateScrollbar({ data: this }, 100));
        this._element.addEventListener('load', this._odooLoadEventCaptureHandler, true);

        _updateScrollbar({ data: this });
    }
};

const _baseHideModal = $.fn.modal.Constructor.prototype._hideModal;
$.fn.modal.Constructor.prototype._hideModal = function () {
    _baseHideModal.apply(this, arguments);

    // Note: do this in all cases, not only for popup with the
    // s_popup_no_backdrop class, as the modal may have lost that class during
    // edition before being closed.
    this._element.classList.remove('s_popup_overflow_page');

    $(this._element).off('content_changed.update_scrollbar');
    $(window).off('resize.update_scrollbar');

    if (this._odooLoadEventCaptureHandler) {
        this._element.removeEventListener('load', this._odooLoadEventCaptureHandler, true);
        delete this._odooLoadEventCaptureHandler;
    }
};

const _baseSetScrollbar = $.fn.modal.Constructor.prototype._setScrollbar;
$.fn.modal.Constructor.prototype._setScrollbar = function () {
    if (this._element.classList.contains('s_popup_no_backdrop')) {
        this._element.classList.toggle('s_popup_overflow_page', !!this._isOverflowingWindow);

        if (!this._isOverflowingWindow) {
            return;
        }
    }
    return _baseSetScrollbar.apply(this, arguments);
};

const _baseGetScrollbarWidth = $.fn.modal.Constructor.prototype._getScrollbarWidth;
$.fn.modal.Constructor.prototype._getScrollbarWidth = function () {
    if (this._element.classList.contains('s_popup_no_backdrop') && !this._isOverflowingWindow) {
        return 0;
    }
    return _baseGetScrollbarWidth.apply(this, arguments);
};

return PopupWidget;
});
