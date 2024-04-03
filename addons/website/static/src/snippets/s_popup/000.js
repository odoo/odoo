odoo.define('website.s_popup', function (require) {
'use strict';

const config = require('web.config');
const dom = require('web.dom');
const publicWidget = require('web.public.widget');
const {getCookie, setCookie} = require('web.utils.cookies');
const {setUtmsHtmlDataset} = require('@website/js/content/inject_dom');

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
            $().getScrollingElement()[0].dispatchEvent(new Event('scroll'));
        }
        this.el.classList.add('d-none');
    },
});

publicWidget.registry.SharedPopup = SharedPopupWidget;

const PopupWidget = publicWidget.Widget.extend({
    selector: '.s_popup',
    events: {
        'click .js_close_popup': '_onCloseClick',
        'hide.bs.modal': '_onHideModal',
        'show.bs.modal': '_onShowModal',
    },
    cookieValue: true,

    /**
     * @override
     */
    start: function () {
        this._popupAlreadyShown = !!getCookie(this.$el.attr('id'));
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
        setCookie(this.el.id, this.cookieValue, nbDays * 24 * 60 * 60, 'required');
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

const noBackdropPopupWidget = publicWidget.Widget.extend({
    selector: '.s_popup_no_backdrop',
    disabledInEditableMode: false,
    events: {
        'shown.bs.modal': '_onModalNoBackdropShown',
        'hide.bs.modal': '_onModalNoBackdropHide',
    },

    /**
     * @override
     */
    start() {
        this.throttledUpdateScrollbar = _.throttle(() => this._updateScrollbar(), 25);
        if (this.editableMode && this.el.classList.contains('show')) {
            // Use case: When the "Backdrop" option is disabled in edit mode.
            // The page scrollbar must be adjusted and events must be added.
            this._updateScrollbar();
            this._addModalNoBackdropEvents();
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this._removeModalNoBackdropEvents();
        // After destroying the widget, we need to trigger a resize event so that
        // the scrollbar can adjust to its default behavior.
        window.dispatchEvent(new Event('resize'));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateScrollbar() {
        // When there is no backdrop the element with the scrollbar is
        // '.modal-content' (see comments in CSS).
        const modalContent = this.el.querySelector('.modal-content');
        const isOverflowing = dom.hasScrollableContent(modalContent);
        const modalInstance = window.Modal.getInstance(this.el);
        if (isOverflowing) {
            // If the "no-backdrop" modal has a scrollbar, the page's scrollbar
            // must be hidden. This is because if the two scrollbars overlap, it
            // is no longer possible to scroll using the modal's scrollbar.
            modalInstance._adjustDialog();
        } else {
            // If the "no-backdrop" modal does not have a scrollbar, the page
            // scrollbar must be displayed because we must be able to scroll the
            // page (e.g. a "cookies bar" popup at the bottom of the page must
            // not prevent scrolling the page).
            modalInstance._resetAdjustments();
        }
    },
    /**
     * @private
     */
    _addModalNoBackdropEvents() {
        window.addEventListener('resize', this.throttledUpdateScrollbar);
        this.resizeObserver = new window.ResizeObserver(() => {
            // When the size of the modal changes, the scrollbar needs to be
            // adjusted.
            this._updateScrollbar();
        });
        this.resizeObserver.observe(this.el.querySelector('.modal-content'));
    },
    /**
     * @private
     */
    _removeModalNoBackdropEvents() {
        window.removeEventListener('resize', this.throttledUpdateScrollbar);
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
            delete this.resizeObserver;
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onModalNoBackdropShown() {
        this._updateScrollbar();
        this._addModalNoBackdropEvents();
    },
    /**
     * @private
     */
    _onModalNoBackdropHide() {
        this._removeModalNoBackdropEvents();
    },
});

publicWidget.registry.noBackdropPopup = noBackdropPopupWidget;

// Extending the popup widget with cookiebar functionality.
// This allows for refusing optional cookies for now and can be
// extended to picking which cookies categories are accepted.
publicWidget.registry.cookies_bar = PopupWidget.extend({
    selector: '#website_cookies_bar',
    events: Object.assign({}, PopupWidget.prototype.events, {
        'click #cookies-consent-essential, #cookies-consent-all': '_onAcceptClick',
    }),

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param ev
     */
    _onAcceptClick(ev) {
        this.cookieValue = `{"required": true, "optional": ${ev.target.id === 'cookies-consent-all'}}`;
        this._onHideModal();
    },
    /**
     * @override
     */
    _onHideModal() {
        this._super(...arguments);
        const params = new URLSearchParams(window.location.search);
        const trackingFields = {
            utm_campaign: "odoo_utm_campaign",
            utm_source: "odoo_utm_source",
            utm_medium: "odoo_utm_medium",
        };
        for (const [key, value] of params) {
            if (key in trackingFields) {
                // Using same cookie expiration value as in python side
                setCookie(trackingFields[key], value, 31 * 24 * 60 * 60, "optional");
            }
        }
        setUtmsHtmlDataset();
    }
});

return PopupWidget;
});
