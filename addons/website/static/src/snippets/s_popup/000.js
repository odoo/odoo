/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import {throttleForAnimation} from "@web/core/utils/timing";
import { getTabableElements, isVisible } from "@web/core/utils/ui";
import { utils as uiUtils, MEDIAS_BREAKPOINTS, SIZES } from "@web/core/ui/ui_service";
import {setUtmsHtmlDataset} from '@website/js/content/inject_dom';
import wUtils from "@website/js/utils";
import { ObservingCookieWidgetMixin } from "@website/snippets/observing_cookie_mixin";

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
            $().getScrollingTarget()[0].dispatchEvent(new Event('scroll'));
        }

        this.el.classList.add('d-none');
    },
});

publicWidget.registry.SharedPopup = SharedPopupWidget;

const PopupWidget = publicWidget.Widget.extend(ObservingCookieWidgetMixin, {
    selector: ".s_popup:not(#website_cookies_bar)",
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
        this.releaseFocus && this.releaseFocus();
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
        this.releaseFocus = this._trapFocus();
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
    /**
     * Traps the focus within the modal.
     *
     * @private
     * @returns {Function} refocuses the element that was focused before the
     * modal opened.
     */
    _trapFocus() {
        let tabableEls = getTabableElements(this.el);
        const previouslyFocusedEl = document.activeElement || document.body;
        if (tabableEls.length) {
            tabableEls[0].focus();
        } else {
            this.el.focus();
        }
        // The focus should stay free for no backdrop popups.
        if (this.el.querySelector(".s_popup_no_backdrop")) {
            return () => previouslyFocusedEl.focus();
        }
        const _onKeydown = (ev) => {
            if (ev.key !== "Tab") {
                return;
            }
            // Update tabableEls: they might have changed in the meantime.
            tabableEls = getTabableElements(this.el);
            if (!tabableEls.length) {
                ev.preventDefault();
                return;
            }
            if (!ev.shiftKey && ev.target === tabableEls[tabableEls.length - 1]) {
                ev.preventDefault();
                tabableEls[0].focus();
            }
            if (ev.shiftKey && ev.target === tabableEls[0]) {
                ev.preventDefault();
                tabableEls[tabableEls.length - 1].focus();
            }
        };
        this.el.addEventListener("keydown", _onKeydown);
        return () => {
            this.el.removeEventListener("keydown", _onKeydown);
            previouslyFocusedEl.focus();
        };
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
        this.releaseFocus && this.releaseFocus();
        // Reset to avoid calling it twice. It may happen with cookie bars or in
        // the destroy.
        this.releaseFocus = null;
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
        const isOverflowing = $(modalContent).hasScrollableContent();
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
        "show_cookies_bar": "_onShowCookiesBar",
    }),

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
        const policyLinkEl = this.el.querySelector(".o_cookies_bar_text_policy");
        if (policyLinkEl && window.location.pathname === new URL(policyLinkEl.href).pathname) {
            this.toggleEl = wUtils.cloneContentEls(`
            <button class="o_cookies_bar_toggle btn btn-info btn-sm rounded-circle d-flex gap-2 align-items-center position-fixed pe-auto">
                <i class="fa fa-eye" alt="" aria-hidden="true"></i> <span class="o_cookies_bar_toggle_label"></span>
            </button>
            `).firstElementChild;
            this.el.insertAdjacentElement("beforebegin", this.toggleEl);
            this._toggleCookiesBar();
            this._onToggleCookiesBar = this._toggleCookiesBar.bind(this);
            this.toggleEl.addEventListener("click", this._onToggleCookiesBar);
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
        cookie.delete(this.el.id);

        const hidden = !popupEl.classList.contains("show");
        this.toggleEl.querySelector(".fa").className = `fa ${hidden ? "fa-eye" : "fa-eye-slash"}`;
        this.toggleEl.querySelector(".o_cookies_bar_toggle_label").innerText = hidden
            ? _t("Show the cookies bar")
            : _t("Hide the cookies bar");
        if (hidden || !popupEl.classList.contains("s_popup_bottom")) {
            this.toggleEl.style.removeProperty("--cookies-bar-toggle-inset-block-end");
        } else {
            // Lazy-loaded images don't have a height yet. We need to await them
            wUtils.onceAllImagesLoaded($(popupEl)).then(() => {
                const popupHeight = popupEl.querySelector(".modal-content").offsetHeight;
                const toggleMargin = 8;
                // Avoid having the toggleEl over another button, but if the
                // cookies bar is too tall, place it at the bottom anyway.
                const bottom = document.body.offsetHeight > popupHeight + this.toggleEl.offsetHeight + toggleMargin
                    ? `calc(
                        ${getComputedStyle(popupEl.querySelector(".modal-dialog")).paddingBottom}
                        + ${popupHeight + toggleMargin}px
                    )`
                    : "";
                this.toggleEl.style.setProperty("--cookies-bar-toggle-inset-block-end", bottom);
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param ev
     */
    _onAcceptClick(ev) {
        const isFullConsent = ev.target.id === "cookies-consent-all";
        this.cookieValue = `{"required": true, "optional": ${isFullConsent}, "ts": ${Date.now()}}`;
        if (isFullConsent) {
            document.dispatchEvent(new Event("optionalCookiesAccepted"));
        }
        this._onHideModal();
        this.toggleEl && this.toggleEl.remove();
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
                cookie.set(trackingFields[key], value, 31 * 24 * 60 * 60, "optional");
            }
        }
        setUtmsHtmlDataset();
    },
    /**
     * Reopens the cookies bar if it was closed.
     *
     * @private
     */
    _onShowCookiesBar() {
        const modalEl = this.el.querySelector(".modal");
        const currCookie = cookie.get(this.el.id);

        if (currCookie && JSON.parse(currCookie).optional || !this._popupAlreadyShown) {
            return;
        }
        $(modalEl).modal("show");

        // The cookies bar remains hidden, most probably because of the browser
        // or an extension: notify the user because "nothing happens when I
        // click" is never good.
        if (!isVisible(modalEl)) {
            window.alert(_t("Our cookies bar was blocked by your browser or an extension."));
            return;
        }
        modalEl.focus();
    },
});

publicWidget.registry.CookiesApproval = publicWidget.Widget.extend({
    selector: "[data-need-cookies-approval]",
    events: {
        "add_cookies_warning": "_onAddCookiesWarning",
    },

    /**
     * @override
     */
    async start() {
        this.iframeEl = this.el.tagName === "IFRAME" ? this.el : this.el.querySelector("iframe");
        if (this.iframeEl) {
            this.optionalCookiesWarningEl = this.iframeEl.nextElementSibling
                ?.classList.contains("o_no_optional_cookie")
                ? this.iframeEl.nextElementSibling
                : null;
            if (!this.optionalCookiesWarningEl) {
                this._addOptionalCookiesWarning();
            }
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        if (this._onWarningElClick && this._onRemoveOptionalCookiesWarning) {
            this.optionalCookiesWarningEl.removeEventListener("click", this._onWarningElClick);
            document.removeEventListener("optionalCookiesAccepted", this._onRemoveOptionalCookiesWarning);
            this._removeOptionalCookiesWarning();
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a warning in place of the iframe. On click, shows the cookies bar if
     * it was hidden.
     *
     * @private
     */
    _addOptionalCookiesWarning() {
        const options = {
            extraStyle: this.iframeEl.parentElement.classList.contains("media_iframe_video")
                ? `aspect-ratio: 16/9; max-width: ${MEDIAS_BREAKPOINTS[SIZES.SM].maxWidth}px;`
                : "",
            extraClasses: getComputedStyle(this.iframeEl.parentElement).position === "absolute"
                ? "" : "my-3",
        };
        this.optionalCookiesWarningEl = renderToElement("website.cookiesWarning", options);
        this.iframeEl.insertAdjacentElement("afterend", this.optionalCookiesWarningEl);
        this.iframeEl.classList.add("d-none");

        this._onWarningElClick = () => {
            $(document.getElementById("website_cookies_bar")).trigger("show_cookies_bar");
        };
        this.optionalCookiesWarningEl.addEventListener("click", this._onWarningElClick);
        this._onRemoveOptionalCookiesWarning = this._removeOptionalCookiesWarning.bind(this);
        document.addEventListener(
            "optionalCookiesAccepted",
            this._onRemoveOptionalCookiesWarning,
            { once: true }
        );
    },
    /**
     * Removes the warning and attributes preventing the iframe from being shown
     *
     * @private
     */
    _removeOptionalCookiesWarning() {
        this.iframeEl.src = this.iframeEl.dataset.nocookieSrc;
        this.iframeEl.classList.remove("d-none");
        delete this.iframeEl.dataset.nocookieSrc;
        delete this.iframeEl.dataset.needCookiesApproval;
        delete this.iframeEl.closest(":not(iframe)[data-need-cookies-approval]")
            ?.dataset.needCookiesApproval;
        this.optionalCookiesWarningEl.remove();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Triggers only on iframes created client-side (for which a widget has not
     * been created): `this.el` is a parent to which the event propagates.
     *
     * @private
     */
    _onAddCookiesWarning(ev) {
        ev.stopPropagation();
        if (!ev.target.nextElementSibling?.classList.contains("o_no_optional_cookie")) {
            this.iframeEl = ev.target;
            this._addOptionalCookiesWarning();
        }
    },
});

export default PopupWidget;
