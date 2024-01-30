odoo.define('website.content.menu', function (require) {
'use strict';

const config = require('web.config');
var publicWidget = require('web.public.widget');
var animations = require('website.content.snippets.animation');
const extraMenuUpdateCallbacks = [];
const weUtils = require('web_editor.utils');
const dom = require('web.dom');

const BaseAnimatedHeader = animations.Animation.extend({
    disabledInEditableMode: false,
    effects: [{
        startEvents: 'scroll',
        update: '_updateHeaderOnScroll',
    }, {
        startEvents: 'resize',
        update: '_updateHeaderOnResize',
    }],

    /**
     * @constructor
     */
    init: function () {
        this._super(...arguments);
        this.fixedHeader = false;
        this.scrolledPoint = 0;
        this.hasScrolled = false;
        this.closeOpenedMenus = false;
        this.scrollHeightTooShort = false;
    },
    /**
     * @override
     */
    start: function () {
        // Used to prevent the editor's unbreakable protection from restoring
        // the menu's auto-hide updates in edit mode.
        this.el.addEventListener("autoMoreMenu.willAdapt", () => this.options.wysiwyg
            && this.options.wysiwyg.odooEditor.unbreakableStepUnactive());
        this.$main = this.$el.next('main');
        this.isOverlayHeader = !!this.$el.closest('.o_header_overlay, .o_header_overlay_theme').length;
        this.$dropdowns = this.$el.find('.dropdown, .dropdown-menu');
        this.$navbarCollapses = this.$el.find('.navbar-collapse');

        // While scrolling through navbar menus on medium devices, body should not be scrolled with it
        this.$navbarCollapses.on('show.bs.collapse.BaseAnimatedHeader', function () {
            if (config.device.size_class <= config.device.SIZES.SM) {
                $(document.body).addClass('overflow-hidden');
            }
        }).on('hide.bs.collapse.BaseAnimatedHeader', function () {
            $(document.body).removeClass('overflow-hidden');
        });

        // We can rely on transitionend which is well supported but not on
        // transitionstart, so we listen to a custom odoo event.
        this._transitionCount = 0;
        this.$el.on('odoo-transitionstart.BaseAnimatedHeader', () => {
            this.el.classList.add('o_transitioning');
            this._adaptToHeaderChangeLoop(1);
        });
        this.$el.on('transitionend.BaseAnimatedHeader', () => this._adaptToHeaderChangeLoop(-1));

        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._toggleFixedHeader(false);
        this.$el.removeClass('o_header_affixed o_header_is_scrolled o_header_no_transition o_transitioning');
        this.$navbarCollapses.off('.BaseAnimatedHeader');
        this.$el.off('.BaseAnimatedHeader');
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adapt the 'right' css property of the header by adding the size of a
     * scrollbar if any.
     *
     * @private
     */
    _adaptFixedHeaderPosition() {
        dom.compensateScrollbar(this.el, this.fixedHeader, false, 'right');
    },
    /**
     * @private
     */
    _adaptToHeaderChange: function () {
        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
        this._updateMainPaddingTop();
        // Take menu into account when `dom.scrollTo()` is used whenever it is
        // visible - be it floating, fully displayed or partially hidden.
        this.el.classList.toggle('o_top_fixed_element', this._isShown());

        for (const callback of extraMenuUpdateCallbacks) {
            callback();
        }
        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
    },
    /**
     * @private
     * @param {integer} [addCount=0]
     */
    _adaptToHeaderChangeLoop: function (addCount = 0) {
        this._adaptToHeaderChange();

        this._transitionCount += addCount;
        this._transitionCount = Math.max(0, this._transitionCount);

        // As long as we detected a transition start without its related
        // transition end, keep updating the main padding top.
        if (this._transitionCount > 0) {
            window.requestAnimationFrame(() => this._adaptToHeaderChangeLoop());

            // The normal case would be to have the transitionend event to be
            // fired but we cannot rely on it, so we use a timeout as fallback.
            if (addCount !== 0) {
                clearTimeout(this._changeLoopTimer);
                this._changeLoopTimer = setTimeout(() => {
                    this._adaptToHeaderChangeLoop(-this._transitionCount);
                }, 500);
            }
        } else {
            // When we detected all transitionend events, we need to stop the
            // setTimeout fallback.
            clearTimeout(this._changeLoopTimer);
            this.el.classList.remove('o_transitioning');
        }
    },
    /**
     * @private
     */
    _computeTopGap() {
        return 0;
    },
    /**
     * @private
     */
    _isShown() {
        return true;
    },
    /**
     * @private
     * @param {boolean} [useFixed=true]
     */
    _toggleFixedHeader: function (useFixed = true) {
        this.fixedHeader = useFixed;
        this._adaptToHeaderChange();
        this.el.classList.toggle('o_header_affixed', useFixed);
        this._adaptFixedHeaderPosition();
    },
    /**
     * @private
     */
    _updateMainPaddingTop: function () {
        this.headerHeight = this.$el.outerHeight();
        this.topGap = this._computeTopGap();

        if (this.isOverlayHeader) {
            return;
        }
        this.$main.css('padding-top', this.fixedHeader ? this.headerHeight : '');
    },
    /**
     * Checks if the size of the header will decrease by adding the
     * 'o_header_is_scrolled' class. If so, we do not add this class if the
     * remaining scroll height is not enough to stay above 'this.scrolledPoint'
     * after the transition, otherwise it causes the scroll position to move up
     * again below 'this.scrolledPoint' and trigger an infinite loop.
     *
     * @todo header effects should be improved in the future to not ever change
     * the page scroll-height during their animation. The code would probably be
     * simpler but also prevent having weird scroll "jumps" during animations
     * (= depending on the logo height after/before scroll, a scroll step (one
     * mousewheel event for example) can be bigger than other ones).
     *
     * @private
     * @returns {boolean}
     */
    _scrollHeightTooShort() {
        const scrollEl = $().getScrollingElement()[0];
        const remainingScroll = (scrollEl.scrollHeight - scrollEl.clientHeight) - this.scrolledPoint;
        const clonedHeader = this.el.cloneNode(true);
        scrollEl.append(clonedHeader);
        clonedHeader.classList.add('o_header_is_scrolled', 'o_header_affixed', 'o_header_no_transition');
        const endHeaderHeight = clonedHeader.offsetHeight;
        clonedHeader.remove();
        const heightDiff = this.headerHeight - endHeaderHeight;
        return heightDiff > 0 ? remainingScroll <= heightDiff : false;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the window is scrolled
     *
     * @private
     * @param {integer} scroll
     */
    _updateHeaderOnScroll: function (scroll) {
        // Disable css transition if refresh with scrollTop > 0
        if (!this.hasScrolled) {
            this.hasScrolled = true;
            if (scroll > 0) {
                this.$el.addClass('o_header_no_transition');
            }
        } else {
            this.$el.removeClass('o_header_no_transition');
            this.closeOpenedMenus = true;
        }

        // Indicates the page is scrolled, the logo size is changed.
        const headerIsScrolled = (scroll > this.scrolledPoint);
        if (this.headerIsScrolled !== headerIsScrolled) {
            this.scrollHeightTooShort = headerIsScrolled && this._scrollHeightTooShort();
            if (!this.scrollHeightTooShort) {
                this.el.classList.toggle('o_header_is_scrolled', headerIsScrolled);
                this.$el.trigger('odoo-transitionstart');
                this.headerIsScrolled = headerIsScrolled;
            }
        }

        if (this.closeOpenedMenus) {
            // TODO master: make this.$dropdowns the .dropdown-toggle directly.
            for (const dropdownMenuEl of this.$dropdowns) {
                Dropdown.getOrCreateInstance(
                    dropdownMenuEl.closest('.dropdown').querySelector('.dropdown-toggle')
                ).hide();
            }
        }
    },
    /**
     * Called when the window is resized
     *
     * @private
     */
    _updateHeaderOnResize: function () {
        this._adaptFixedHeaderPosition();
        if (document.body.classList.contains('overflow-hidden')
                && config.device.size_class > config.device.SIZES.SM) {
            document.body.classList.remove('overflow-hidden');
            this.$el.find('.navbar-collapse').removeClass('show');
        }
    },
});

publicWidget.registry.StandardAffixedHeader = BaseAnimatedHeader.extend({
    selector: 'header.o_header_standard:not(.o_header_sidebar)',

    /**
     * @constructor
     */
    init: function () {
        this._super(...arguments);
        this.fixedHeaderShow = false;
        this.scrolledPoint = 300;
    },
    /**
     * @override
     */
    start: function () {
        this.headerHeight = this.$el.outerHeight();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy() {
        this.$el.css('transform', '');
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _isShown() {
        return !this.fixedHeader || this.fixedHeaderShow;
    },
    /**
     * Called when the window is scrolled
     *
     * @override
     * @param {integer} scroll
     */
    _updateHeaderOnScroll: function (scroll) {
        this._super(...arguments);

        const mainPosScrolled = (scroll > this.headerHeight + this.topGap);
        const reachPosScrolled = (scroll > this.scrolledPoint + this.topGap) && !this.scrollHeightTooShort;
        const fixedUpdate = (this.fixedHeader !== mainPosScrolled);
        const showUpdate = (this.fixedHeaderShow !== reachPosScrolled);

        if (fixedUpdate || showUpdate) {
            this.$el.css('transform',
                reachPosScrolled
                ? `translate(0, -${this.topGap}px)`
                : mainPosScrolled
                ? 'translate(0, -100%)'
                : '');
            void this.$el[0].offsetWidth; // Force a paint refresh
        }

        this.fixedHeaderShow = reachPosScrolled;

        if (fixedUpdate) {
            this._toggleFixedHeader(mainPosScrolled);
        } else if (showUpdate) {
            this._adaptToHeaderChange();
        }
    },
});

publicWidget.registry.FixedHeader = BaseAnimatedHeader.extend({
    selector: 'header.o_header_fixed:not(.o_header_sidebar)',

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateHeaderOnScroll: function (scroll) {
        this._super(...arguments);
        // Need to be 'unfixed' when the window is not scrolled so that the
        // transparent menu option still works.
        if (scroll > (this.scrolledPoint + this.topGap)) {
            if (!this.$el.hasClass('o_header_affixed')) {
                this.$el.css('transform', `translate(0, -${this.topGap}px)`);
                void this.$el[0].offsetWidth; // Force a paint refresh
                this._toggleFixedHeader(true);
            }
        } else {
            this._toggleFixedHeader(false);
            void this.$el[0].offsetWidth; // Force a paint refresh
            this.$el.css('transform', '');
        }
    },
});

const BaseDisappearingHeader = publicWidget.registry.FixedHeader.extend({
    /**
     * @override
     */
    init: function () {
        this._super(...arguments);
        this.scrollingDownwards = true;
        this.hiddenHeader = false;
        this.position = 0;
        this.atTop = true;
        this.checkPoint = 0;
        this.scrollOffsetLimit = 200;
    },
    /**
     * @override
     */
    destroy: function () {
        this._showHeader();
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _hideHeader: function () {
        this.$el.trigger('odoo-transitionstart');
    },
    /**
     * @override
     */
    _isShown() {
        return !this.fixedHeader || !this.hiddenHeader;
    },
    /**
     * @private
     */
    _showHeader: function () {
        this.$el.trigger('odoo-transitionstart');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateHeaderOnScroll: function (scroll) {
        this._super(...arguments);

        const scrollingDownwards = (scroll > this.position);
        const atTop = (scroll <= 0);
        if (scrollingDownwards !== this.scrollingDownwards) {
            this.checkPoint = scroll;
        }

        this.scrollingDownwards = scrollingDownwards;
        this.position = scroll;
        this.atTop = atTop;

        if (scrollingDownwards) {
            if (!this.hiddenHeader && scroll - this.checkPoint > (this.scrollOffsetLimit + this.topGap)) {
                this.hiddenHeader = true;
                this._hideHeader();
            }
        } else {
            if (this.hiddenHeader && scroll - this.checkPoint < -(this.scrollOffsetLimit + this.topGap) / 2) {
                this.hiddenHeader = false;
                this._showHeader();
            }
        }

        if (atTop && !this.atTop) {
            // Force reshowing the invisible-on-scroll sections when reaching
            // the top again
            this._showHeader();
        }
    },
});

publicWidget.registry.DisappearingHeader = BaseDisappearingHeader.extend({
    selector: 'header.o_header_disappears:not(.o_header_sidebar)',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _hideHeader: function () {
        this._super(...arguments);
        this.$el.css('transform', 'translate(0, -100%)');
    },
    /**
     * @override
     */
    _showHeader: function () {
        this._super(...arguments);
        this.$el.css('transform', this.atTop ? '' : `translate(0, -${this.topGap}px)`);
    },
});

publicWidget.registry.FadeOutHeader = BaseDisappearingHeader.extend({
    selector: 'header.o_header_fade_out:not(.o_header_sidebar)',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _hideHeader: function () {
        this._super(...arguments);
        this.$el.stop(false, true).fadeOut();
    },
    /**
     * @override
     */
    _showHeader: function () {
        this._super(...arguments);
        this.$el.css('transform', this.atTop ? '' : `translate(0, -${this.topGap}px)`);
        this.$el.stop(false, true).fadeIn();
    },
});

/**
 * Note: this works well with the affixMenu... by chance (menuDirection is
 * called after alphabetically).
 *
 * @todo @deprecated For the moment, dynamic positioning of dropdown elements is
 * explicitly disabled by Bootstrap on dropdowns that are in the navbar. In
 * master, we will patch the BS dropdown to allow this and remove the following
 * widget.
 */
publicWidget.registry.menuDirection = publicWidget.Widget.extend({
    selector: 'header .navbar .nav',
    disabledInEditableMode: false,
    events: {
        'show.bs.dropdown': '_onDropdownShow',
    },

    /**
     * @override
     */
    start: function () {
        this.defaultAlignment = this.$el.is('.ms-auto, .ms-auto ~ *') ? 'end' : 'start';
        this.isRtl = !!this.el.closest('#wrapwrap.o_rtl');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} alignment - either 'start' or 'end'
     * @param {integer} liOffset
     * @param {integer} liWidth
     * @param {integer} menuWidth
     * @param {integer} pageWidth
     * @returns {boolean}
     */
    _checkOpening: function (alignment, liOffset, liWidth, menuWidth, pageWidth) {
        if (alignment === 'start' && !this.isRtl || alignment === 'end' && this.isRtl) {
            // Check if ok to open the dropdown to the right (no window overflow)
            return (liOffset + menuWidth <= pageWidth);
        } else {
            // Check if ok to open the dropdown to the left (no window overflow)
            return (liOffset + liWidth - menuWidth >= 0);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onDropdownShow: function (ev) {
        const $dropdown = $(ev.target).closest('.dropdown, .dropup');
        var $menu = $dropdown.children('.dropdown-menu');
        var liOffset = $dropdown.offset().left;
        var liWidth = $dropdown.outerWidth();
        var menuWidth = $menu.outerWidth();
        var pageWidth = $('#wrapwrap').outerWidth();

        $menu.removeClass('dropdown-menu-start dropdown-menu-end');

        var alignment = this.defaultAlignment;
        if ($dropdown.nextAll(':visible').length === 0) {
            // The dropdown is the last menu item, open to the left side
            // (right side with rtl languages).
            alignment = 'end';
        }

        // If can't open in the current direction because it would overflow the
        // page, change the direction. But if the other direction would do the
        // same, change back the direction.
        for (var i = 0; i < 2; i++) {
            if (!this._checkOpening(alignment, liOffset, liWidth, menuWidth, pageWidth)) {
                alignment = (alignment === 'start' ? 'end' : 'start');
            }
        }

        $menu.addClass('dropdown-menu-' + alignment);
    },
});

publicWidget.registry.hoverableDropdown = animations.Animation.extend({
    selector: 'header.o_hoverable_dropdown',
    disabledInEditableMode: false,
    effects: [{
        startEvents: 'resize',
        update: '_dropdownHover',
    }],
    events: {
        'mouseenter .dropdown': '_onMouseEnter',
        'mouseleave .dropdown': '_onMouseLeave',
    },

    /**
     * @override
     */
    start: function () {
        if (this.editableMode) {
            this._onPageClick = this._onPageClick.bind(this);
            this.el.closest('#wrapwrap').addEventListener('click', this._onPageClick, {capture: true});
        }
        this.$dropdownMenus = this.$el.find('.dropdown-menu');
        this.$dropdownToggles = this.$el.find('.dropdown-toggle');
        this._dropdownHover();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy() {
        if (this.editableMode) {
            this.el.closest('#wrapwrap').removeEventListener('click', this._onPageClick, {capture: true});
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _dropdownHover: function () {
        this.$dropdownMenus.attr('data-bs-popper', 'none');
        if (config.device.size_class > config.device.SIZES.SM) {
            this.$dropdownMenus.css('margin-top', '0');
            this.$dropdownMenus.css('top', 'unset');
        } else {
            this.$dropdownMenus.css('margin-top', '');
            this.$dropdownMenus.css('top', '');
        }
    },
    /**
     * Hides all opened dropdowns.
     *
     * @private
     */
    _hideDropdowns() {
        for (const toggleEl of this.el.querySelectorAll('.dropdown-toggle.show')) {
            Dropdown.getOrCreateInstance(toggleEl).hide();
        }
    },
    /**
     * @private
     * @param {Event} ev
     * @param {String} method bootstrap dropdowns method name
     */
    _updateDropdownVisibility: function (ev, method) {
        const { currentTarget } = ev;
        if (config.device.size_class <= config.device.SIZES.SM) {
            return;
        }
        if (currentTarget.classList.contains('o_extra_menu_items')) {
            return;
        }
        const dropdownToggle = currentTarget.querySelector('.dropdown-toggle');
        if (dropdownToggle) {
            Dropdown.getOrCreateInstance(dropdownToggle)[method]();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onMouseEnter: function (ev) {
        if (this.editableMode) {
            // Do not handle hover if another dropdown is opened.
            if (this.el.querySelector('.dropdown-toggle.show')) {
                return;
            }
        }
        // Get the previously focused element of the page.
        const focusedEl = this.el.ownerDocument.querySelector(":focus")
            || window.frameElement && window.frameElement.ownerDocument.querySelector(":focus");

        // The user must click on the dropdown if he is on mobile (no way to
        // hover) or if the dropdown is the extra menu ('+').
        this._updateDropdownVisibility(ev, 'show');

        // Keep the focus on the previously focused element if any, otherwise do
        // not focus the dropdown on hover.
        if (focusedEl) {
            focusedEl.focus();
        } else {
            ev.currentTarget.querySelector(".dropdown-toggle").blur();
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseLeave: function (ev) {
        if (this.editableMode) {
            // Cancel handling from view mode.
            return;
        }
        this._updateDropdownVisibility(ev, 'hide');
    },
    /**
     * Called when the page is clicked anywhere.
     * Closes the shown dropdown if the click is outside of it.
     *
     * @private
     * @param {Event} ev
     */
    _onPageClick(ev) {
        if (ev.target.closest('.dropdown-menu.show')) {
            return;
        }
        this._hideDropdowns();
    },
});

publicWidget.registry.HeaderMainCollapse = publicWidget.Widget.extend({
    selector: 'header#top',
    disabledInEditableMode: false,
    events: {
        'show.bs.collapse #top_menu_collapse': '_onCollapseShow',
        'hidden.bs.collapse #top_menu_collapse': '_onCollapseHidden',
    },

    /**
     * @override
     */
    start() {
        // This is a fix in stable to move the language switcher in the navbar
        // when the "off-canvas" mobile menu is enabled. Without this the
        // language switcher is inaccessible in the "off-canvas" mobile menu.
        // TODO: Remove this in master and make the adaptations only in the XML
        // templates.
        this.languageSelectorMustBeMoved = false;
        // If mobile menu is "off-canvas".
        if (this.$target[0].querySelector('.o_offcanvas_menu_toggler')) {
            this.navbarEl = this.$target[0].querySelector('#top_menu');
            this.languageSelectorEl = this.$target[0].querySelectorAll('#top_menu_collapse .js_language_selector');
            // As there are 2 language selectors in 'template_header_vertical',
            // we have to do this to be sure to move the last of the 2 (the one
            // displayed on mobile).
            this.languageSelectorEl = this.languageSelectorEl[this.languageSelectorEl.length - 1];
            this.languageSelectorMustBeMoved = this.languageSelectorEl
                && !this.navbarEl.contains(this.languageSelectorEl);
            // Specific case with the "hamburger full" header template where
            // there is the same bug with the call to action.
            if (this.$target[0].querySelector('.o_header_hamburger_full_toggler')) {
                const callToActionEl = this.$target[0].querySelector('.oe_structure_solo');
                if (callToActionEl) {
                    this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
                    callToActionEl.classList.add('nav-item');
                    this.navbarEl.append(callToActionEl);
                    this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
                }
            }
            // Specific case with the "boxed" header template where the "call to
            // action" button is inaccessible in the "off-canvas" mobile menu.
            this.offcanvasAndBoxedHeader = false;
            if (weUtils.getCSSVariableValue('header-template').includes('boxed')) {
                this.boxedHeaderCallToActionEl = this.$target[0].querySelector('#top_menu_collapse .oe_structure_solo');
                this.offcanvasAndBoxedHeader = !!this.boxedHeaderCallToActionEl;
            }
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCollapseShow() {
        this.el.classList.add('o_top_menu_collapse_shown');
        if (this.languageSelectorMustBeMoved) {
            this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
            this.languageSelectorEl.classList.add('nav-item');
            this.navbarEl.append(this.languageSelectorEl);
            this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
        }
        if (this.offcanvasAndBoxedHeader) {
            this.boxedHeaderCallToActionEl.classList.add('nav-item');
            this.navbarEl.append(this.boxedHeaderCallToActionEl);
        }
    },
    /**
     * @private
     */
    _onCollapseHidden() {
        this.el.classList.remove('o_top_menu_collapse_shown');
        if (this.languageSelectorMustBeMoved) {
            this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
            this.languageSelectorEl.classList.remove('nav-item');
            this.navbarEl.after(this.languageSelectorEl);
            this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerActive();
        }
        if (this.offcanvasAndBoxedHeader) {
            this.boxedHeaderCallToActionEl.classList.remove('nav-item');
            this.navbarEl.after(this.boxedHeaderCallToActionEl);
        }
    },
});

return {
    extraMenuUpdateCallbacks: extraMenuUpdateCallbacks,
};
});
