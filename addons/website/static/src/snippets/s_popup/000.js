/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { cookie } from "@web/core/browser/cookie";
import dom from "@web/legacy/js/core/dom";
import {throttleForAnimation} from "@web/core/utils/timing";
import { utils as uiUtils } from "@web/core/ui/ui_service";

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

        // Popup are always closed when entering edit mode (see PopupWidget),
        // this allows to make sure the class is sync on the .s_popup parent
        // after that moment too.
        if (!this.editableMode) {
            this.el.classList.add('d-none');
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onModalShow() {
        this.el.classList.remove('d-none');
    },
    /**
     * @private
     */
    _onModalHidden() {
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
        'click .btn-primary': '_onBtnPrimaryClick',
        'hide.bs.modal': '_onHideModal',
        'show.bs.modal': '_onShowModal',
    },
    cookieValue: true,

    /**
     * @override
     */
    start: function () {
        this.modalShownOnClickEl = this.el.querySelector(".modal[data-display='onClick']");
        if (this.modalShownOnClickEl) {
            // We add a "hashchange" listener in case a button to open a popup
            // is clicked.
            this.__onHashChange = this._onHashChange.bind(this);
            window.addEventListener('hashchange', this.__onHashChange);
            // Check if a hash exists and if the modal needs to be opened when
            // the page loads (e.g. The user has clicked a button on the
            // "Contact us" page to open a popup on the homepage).
            this._showPopupOnClick();
        } else {
            this._popupAlreadyShown = !!cookie.get(this.$el.attr('id'));
            if (!this._popupAlreadyShown) {
                this._bindPopup();
            }
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        $(document).off('mouseleave.open_popup');
        this.$el.find('.modal').modal('hide');
        clearTimeout(this.timeout);
        if (this.modalShownOnClickEl) {
            window.removeEventListener('hashchange', this.__onHashChange);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _bindPopup: function () {
        const $main = this.$el.find('.modal');

        let display = $main.data('display');
        let delay = $main.data('showAfter');

        if (uiUtils.isSmall()) {
            if (display === 'mouseExit') {
                display = 'afterDelay';
                delay = 5000;
            }
        }

        if (display === 'afterDelay') {
            this.timeout = setTimeout(() => this._showPopup(), delay);
        } else if (display === "mouseExit") {
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
        this.$el.find('.modal').modal('hide');
    },
    /**
     * @private
     */
    _showPopup: function () {
        if (this._popupAlreadyShown || !this._canShowPopup()) {
            return;
        }
        this.$el.find('.modal').modal('show');
    },
    /**
     * @private
     */
    _showPopupOnClick() {
        const hash = window.location.hash;
        // If a hash exists in the URL and it corresponds to the ID of the modal,
        // then we open the modal.
        if (hash && hash.substring(1) === this.modalShownOnClickEl.id) {
            // We remove the hash from the URL because otherwise the popup
            // cannot open again after being closed.
            const urlWithoutHash = window.location.href.replace(hash, '');
            window.history.replaceState(null, null, urlWithoutHash);
            this._showPopup();
        }
    },
    /**
     * Checks if the given primary button should allow or not to close the
     * modal.
     *
     * @private
     * @param {HTMLElement} primaryBtnEl
     */
    _canBtnPrimaryClosePopup(primaryBtnEl) {
        return !(
            primaryBtnEl.classList.contains("s_website_form_send")
            || primaryBtnEl.classList.contains("o_website_form_send")
        );
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
    _onBtnPrimaryClick(ev) {
        if (this._canBtnPrimaryClosePopup(ev.target)) {
            this._hidePopup();
        }
    },
    /**
     * @private
     */
    _onHideModal: function () {
        const nbDays = this.$el.find('.modal').data('consentsDuration');
        cookie.set(this.el.id, this.cookieValue, nbDays * 24 * 60 * 60, 'required');
        this._popupAlreadyShown = true && !this.modalShownOnClickEl;

        this.$el.find('.media_iframe_video iframe').each((i, iframe) => {
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
    /**
     * @private
     */
    _onHashChange() {
        this._showPopupOnClick();
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
        this.throttledUpdateScrollbar = throttleForAnimation(() => this._updateScrollbar());
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
        this.throttledUpdateScrollbar.cancel();
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
});

export default PopupWidget;
