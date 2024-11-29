import publicWidget from "@web/legacy/js/public/public_widget";
import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { utils as uiUtils, SIZES } from "@web/core/ui/ui_service";
import { ObservingCookieWidgetMixin } from "@website/snippets/observing_cookie_mixin";

// TODO: remove PopupWidget, kept for compatibility with other widgets not yet
// turned into interactions.
const PopupWidget = publicWidget.Widget.extend(ObservingCookieWidgetMixin, {
    // selector: ".s_popup:not(#website_cookies_bar)",
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
            // Check if every child element of the popup is conditionally hidden,
            // and if so, never show an empty popup.
            // config.device.isMobile is true if the device is <= SM, but the device
            // visibility option uses < LG to hide on mobile. So compute it here.
            const isMobile = uiUtils.getSize() < SIZES.LG;
            const emptyPopup = [
                ...this.$el[0].querySelectorAll(".oe_structure > *:not(.s_popup_close)")
            ].every((el) => {
                const visibilitySelectors = el.dataset.visibilitySelectors;
                const deviceInvisible = isMobile
                    ? el.classList.contains("o_snippet_mobile_invisible")
                    : el.classList.contains("o_snippet_desktop_invisible");
                return (visibilitySelectors && el.matches(visibilitySelectors)) || deviceInvisible;
            });
            if (!this._popupAlreadyShown && !emptyPopup) {
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
    _showPopupOnClick(hash = window.location.hash) {
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
            // TODO still oeExpression to remove someday
            this._manageIframeSrc(media, media.dataset.oeExpression || media.dataset.src);
        });
    },
    /**
     * @private
     */
    _onHashChange(ev) {
        // Keep the new hash from the event to avoid conflict with the eCommerce
        // hash attributes managing.
        // TODO : it should not have been a hash at all for ecommerce, but a
        // query string parameter
        this._showPopupOnClick(new URL(ev.newURL).hash);
    },
});

publicWidget.registry.popup = PopupWidget;

export default PopupWidget;
