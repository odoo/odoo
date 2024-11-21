/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import animations from "@website/js/content/snippets.animation";
export const extraMenuUpdateCallbacks = [];
import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import { compensateScrollbar } from "@web/core/utils/scrolling";

// The header height may vary with sections hidden on scroll (see the class
// `o_header_hide_on_scroll`). To avoid scroll jumps, we cache the value.
let headerHeight;

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
        this.scrollableEl = $().getScrollingElement()[0];
    },
    /**
     * @override
     */
    start: function () {
        this.$main = this.$el.next('main');
        this.isOverlayHeader = !!this.$el.closest('.o_header_overlay, .o_header_overlay_theme').length;
        this.hiddenOnScrollEl = this.el.querySelector(".o_header_hide_on_scroll");

        // While scrolling through navbar menus on medium devices, body should
        // not be scrolled with it.
        const disableScroll = function () {
            if (uiUtils.getSize() < SIZES.LG) {
                $(document.body).addClass('overflow-hidden');
            }
        };
        const enableScroll = function () {
            $(document.body).removeClass('overflow-hidden');
        };
        this.$navbarOffcanvases = this.$el.find(".offcanvas");
        this.$navbarOffcanvases
            .on("show.bs.offcanvas.BaseAnimatedHeader", disableScroll)
            .on("hide.bs.offcanvas.BaseAnimatedHeader", enableScroll);

        // Compatibility: can probably be removed, there is no such elements in
        // default navbars... although it could be used by custo.
        this.$navbarCollapses = this.$el.find('.navbar-collapse');
        this.$navbarCollapses
            .on("show.bs.collapse.BaseAnimatedHeader", disableScroll)
            .on("hide.bs.collapse.BaseAnimatedHeader", enableScroll);

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
        this.$navbarOffcanvases.off(".BaseAnimatedHeader");
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
        compensateScrollbar(this.el, this.fixedHeader, false, 'right');
    },
    /**
     * @private
     */
    _adaptToHeaderChange: function () {
        this.options.wysiwyg && this.options.wysiwyg.odooEditor.observerUnactive();
        this._updateMainPaddingTop();
        // Take menu into account when `scrollTo()` is used whenever it is
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
     * Scrolls to correctly display the section specified in the URL
     *
     * @private
     */
    _adjustUrlAutoScroll() {
        // When the url contains #aRandomSection, prevent the navbar to overlap
        // on the section, for this, we scroll as many px as the navbar height.
        if (!this.editableMode) {
            this.scrollableEl.scrollBy(0, -this.el.offsetHeight);
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
        headerHeight ||= this.el.getBoundingClientRect().height;
        this.topGap = this._computeTopGap();

        if (this.isOverlayHeader) {
            return;
        }
        this.$main.css('padding-top', this.fixedHeader ? headerHeight : '');
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
        const scrollEl = this.scrollableEl;
        const remainingScroll = (scrollEl.scrollHeight - scrollEl.clientHeight) - this.scrolledPoint;
        const clonedHeader = this.el.cloneNode(true);
        scrollEl.append(clonedHeader);
        clonedHeader.classList.add('o_header_is_scrolled', 'o_header_affixed', 'o_header_no_transition');
        const endHeaderHeight = clonedHeader.offsetHeight;
        clonedHeader.remove();
        const heightDiff = headerHeight - endHeaderHeight;
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
                this._adjustUrlAutoScroll();
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
            // Hide only the open dropdowns.
            this.el.querySelectorAll(".dropdown-toggle.show").forEach(dropdownToggleEl => {
                Dropdown.getOrCreateInstance(dropdownToggleEl).hide();
            });
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
                && uiUtils.getSize() >= SIZES.LG) {
            this.el.querySelectorAll(".offcanvas.show").forEach(offcanvasEl => {
                Offcanvas.getOrCreateInstance(offcanvasEl).hide();
            });
            // Compatibility: can probably be removed, there is no such elements
            // in default navbars... although it could be used by custo.
            this.el.querySelectorAll(".navbar-collapse.show").forEach(collapseEl => {
                Collapse.getOrCreateInstance(collapseEl).hide();
            });
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
        headerHeight ||= this.el.getBoundingClientRect().height;
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

        const mainPosScrolled = (scroll > headerHeight + this.topGap);
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
        this.hiddenOnScrollEl?.classList.toggle("hidden", mainPosScrolled);

        if (fixedUpdate) {
            this._toggleFixedHeader(mainPosScrolled);
        } else if (showUpdate) {
            this._adaptToHeaderChange();
        }
    },
});

publicWidget.registry.FixedHeader = BaseAnimatedHeader.extend({
    selector: 'header.o_header_fixed:not(.o_header_sidebar)',

    /**
     * @override
     */
    start() {
        const _super = this._super(...arguments);
        this.dropdownToggleEls = [];
        if (this.hiddenOnScrollEl) {
            this.dropdownToggleEls = this.hiddenOnScrollEl.querySelectorAll(".dropdown-toggle");
            for (const dropdownToggleEl of this.dropdownToggleEls) {
                this.__onDropdownShow = this._onDropdownShow.bind(this);
                dropdownToggleEl.addEventListener("show.bs.dropdown", this.__onDropdownShow);
            }
            this.searchbarEl = this.hiddenOnScrollEl
                .querySelector(":not(.modal-content) > .o_searchbar_form");
            if (this.searchbarEl) {
                this.__onSearchbarInput = this._onSearchbarInput.bind(this);
                this.searchbarEl.addEventListener("input", this.__onSearchbarInput);
            }
        }
        return _super;
    },
    /**
     * @override
     */
    destroy() {
        for (const dropdownToggleEl of this.dropdownToggleEls) {
            dropdownToggleEl.removeEventListener("show.bs.dropdown", this.__onDropdownShow);
        }
        if (this.searchbarEl) {
            this.searchbarEl.removeEventListener("input", this.__onSearchbarInput);
        }
        this._super(...arguments);
    },

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

        if (this.hiddenOnScrollEl) {
            let elHeight = 0;
            if (this.fixedHeader && this.searchbarEl?.matches(".show")) {
                // Close the dropdown of the search bar if it's open when
                // scrolling. Otherwise, the calculated height of the
                // 'hiddenOnScrollEl' element will be incorrect because it will
                // include the dropdown height.
                this.searchbarEl.querySelector("input").blur();
                elHeight = this.hiddenOnScrollEl.offsetHeight;
            } else {
                elHeight = this.hiddenOnScrollEl.scrollHeight;
            }
            const scrollDelta = window.matchMedia(`(prefers-reduced-motion: reduce)`).matches ?
                scroll : Math.floor(scroll / 4);
            elHeight = Math.max(0, elHeight - scrollDelta);
            this.hiddenOnScrollEl.classList.toggle("hidden", elHeight === 0);
            if (elHeight === 0) {
                this.hiddenOnScrollEl.removeAttribute("style");
            } else {
                // When the page hasn't been scrolled yet, we don't set overflow
                // to hidden. Without this, the dropdowns would be invisible.
                // (e.g., "user menu" dropdown).
                this.hiddenOnScrollEl.style.overflow = this.fixedHeader ? "hidden" : "";
                this.hiddenOnScrollEl.style.height = this.fixedHeader ? `${elHeight}px` : "";
                let elPadding = parseInt(getComputedStyle(this.hiddenOnScrollEl).paddingBlock);
                if (elHeight < elPadding * 2) {
                    const heightDifference = elPadding * 2 - elHeight;
                    elPadding = Math.max(0, elPadding - Math.floor(heightDifference / 2));
                    this.hiddenOnScrollEl.style
                        .setProperty("padding-block", `${elPadding}px`, "important");
                } else {
                    this.hiddenOnScrollEl.style.paddingBlock = "";
                }
                if (this.fixedHeader) {
                    // The height of the "hiddenOnScrollEl" element changes, so
                    // the height of the header also changes. Therefore, we need
                    // to get the current height of the header and then to
                    // update the top padding of the main element.
                    headerHeight = this.el.getBoundingClientRect().height;
                    this._updateMainPaddingTop();
                }
            }
            if (!this.fixedHeader && this.dropdownClickedEl) {
                const dropdown = Dropdown.getOrCreateInstance(this.dropdownClickedEl);
                dropdown.show();
                this.dropdownClickedEl = null;
            }
        }
    },
    /**
     * Called when a dropdown within 'this.hiddenOnScrollEl' is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onDropdownShow(ev) {
        // If a dropdown inside the element 'this.hiddenOnScrollEl' is clicked
        // while the header is fixed, we need to scroll the page up so that the
        // 'this.hiddenOnScrollEl' element is no longer overflow hidden. Without
        // this, the dropdown would be invisible.
        if (this.fixedHeader) {
            ev.preventDefault();
            this.scrollableEl.scrollTo({ top: 0, behavior: "smooth" });
            this.dropdownClickedEl = ev.currentTarget;
        }
    },
    /**
     * Called when a searchbar within 'this.hiddenOnScrollEl' receives input.
     *
     * @private
     * @param {Event} ev
     */
    _onSearchbarInput(ev) {
        // Prevents the dropdown with search results from being hidden when the
        // header is fixed (see comment in '_onDropdownClick').
        // The scroll animation is instantaneous because the dropdown could open
        // before reaching the top of the page, which would result in an
        // incorrect calculated height of the header.
        if (this.fixedHeader) {
            this.scrollableEl.scrollTo({ top: 0 });
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
    _adjustUrlAutoScroll() {},
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
    _adjustUrlAutoScroll() {},
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
        this.$dropdownMenus = this.$el.find('.dropdown-menu');
        this.$dropdownToggles = this.$el.find('.dropdown-toggle');
        this._dropdownHover();
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
        if (uiUtils.getSize() >= SIZES.LG) {
            this.$dropdownMenus.css('margin-top', '0');
            this.$dropdownMenus.css('top', 'unset');
        } else {
            this.$dropdownMenus.css('margin-top', '');
            this.$dropdownMenus.css('top', '');
        }
    },
    /**
     * @private
     * @param {Event} ev
     * @param {boolean} [doShow=true] true to show, false to hide
     */
    _updateDropdownVisibility(ev, doShow = true) {
        if (uiUtils.getSize() < SIZES.LG) {
            return;
        }
        if (ev.currentTarget.closest('.o_extra_menu_items')) {
            return;
        }
        const dropdownToggleEl = ev.currentTarget.querySelector('.dropdown-toggle');
        if (!dropdownToggleEl) {
            return;
        }
        const dropdown = Dropdown.getOrCreateInstance(dropdownToggleEl);
        if (doShow) {
            dropdown.show();
        } else {
            dropdown.hide();
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
        // hover) or if the dropdown is the (or in the) extra menu ('+').
        this._updateDropdownVisibility(ev, true);

        // Keep the focus on the previously focused element if any, otherwise do
        // not focus the dropdown on hover.
        if (focusedEl) {
            focusedEl.focus({preventScroll: true});
        } else {
            const dropdownToggleEl = ev.currentTarget.querySelector(".dropdown-toggle");
            if (dropdownToggleEl) {
                dropdownToggleEl.blur();
            }
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
        this._updateDropdownVisibility(ev, false);
    },
});

publicWidget.registry.MegaMenuDropdown = publicWidget.Widget.extend({
    selector: "header#top",
    disabledInEditableMode: false,
    events: {
        "mousedown .o_mega_menu_toggle": "_onMegaMenuClick",
        "mouseenter .o_mega_menu_toggle": "_onMegaMenuHover",
        "mousedown .o_extra_menu_items": "_onExtraMenuClick",
        "keyup .o_mega_menu_toggle": "_onMegaMenuClick",
        "keyup .o_extra_menu_items": "_onExtraMenuClick",
    },

    /**
     * @override
     */
    start() {
        const toggleEls = this.el.querySelectorAll(".o_mega_menu_toggle");
        this.desktopMegaMenuToggleEls = [];
        this.mobileMegaMenuToggleEls = [];
        for (const el of toggleEls) {
            if (el.closest(".o_header_mobile")) {
                this.mobileMegaMenuToggleEls.push(el);
            } else {
                this.desktopMegaMenuToggleEls.push(el);
            }
        }

        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * If the mega menu dropdown on which we are clicking/hovering does not have
     * a mega menu (i.e. it is in the other navbar), brings the corresponding
     * mega menu into it.
     *
     * @private
     * @param {Element} megaMenuToggleEl the clicked/hovered mega menu dropdown
     */
    _moveMegaMenu(megaMenuToggleEl) {
        const hasMegaMenu = !!megaMenuToggleEl.parentElement.querySelector(".o_mega_menu");
        if (hasMegaMenu) {
            return;
        }
        this.options.wysiwyg?.odooEditor.observerUnactive("moveMegaMenu");
        const isMobileNavbar = !!megaMenuToggleEl.closest(".o_header_mobile");
        const currentNavbarToggleEls = isMobileNavbar ?
            this.mobileMegaMenuToggleEls : this.desktopMegaMenuToggleEls;
        const otherNavbarToggleEls = isMobileNavbar ?
            this.desktopMegaMenuToggleEls : this.mobileMegaMenuToggleEls;
        const megaMenuToggleIndex = currentNavbarToggleEls.indexOf(megaMenuToggleEl);
        const previousMegaMenuToggleEl = otherNavbarToggleEls[megaMenuToggleIndex];
        const megaMenuEl = previousMegaMenuToggleEl.parentElement.querySelector(".o_mega_menu");
        // Hiding the dropdown where the mega menu comes from before moving it,
        // so everything is in a consistent state.
        Dropdown.getOrCreateInstance(previousMegaMenuToggleEl).hide();
        megaMenuToggleEl.insertAdjacentElement("afterend", megaMenuEl);
        this.options.wysiwyg?.odooEditor.observerActive("moveMegaMenu");
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a mega menu dropdown is clicked/key pressed.
     *
     * @private
     * @param {Event} ev
     */
    _onMegaMenuClick(ev) {
        const megaMenuToggleEl = ev.currentTarget;
        // Ignore the event if the menus are hoverable and in desktop view (the
        // hoverable menus are clicked on mobile view), but not if we used the
        // keyboard.
        if (this.el.classList.contains("o_hoverable_dropdown")
                && !megaMenuToggleEl.closest(".o_header_mobile") && ev.type !== "keyup") {
            return;
        }
        this._moveMegaMenu(megaMenuToggleEl);
    },
    /**
     * Called when a mega menu dropdown is hovered.
     *
     * @private
     * @param {Event} ev
     */
    _onMegaMenuHover(ev) {
        const megaMenuToggleEl = ev.currentTarget;
        // Ignore the event if the menus are not hoverable or if we are in
        // mobile view (again, the hoverable menus are clicked on mobile view).
        if (!this.el.classList.contains("o_hoverable_dropdown")
                || megaMenuToggleEl.closest(".o_header_mobile")) {
            return;
        }
        this._moveMegaMenu(megaMenuToggleEl);
    },
    /**
     * Called when the extra menu (+) dropdown is clicked/key pressed.
     *
     * @private
     * @param {Event} ev
     */
    _onExtraMenuClick(ev) {
        const megaMenuToggleEls = ev.currentTarget.querySelectorAll(".o_mega_menu_toggle");
        megaMenuToggleEls.forEach(megaMenuToggleEl => this._moveMegaMenu(megaMenuToggleEl));
    },
});

publicWidget.registry.HeaderGeneral = publicWidget.Widget.extend({
    selector: 'header#top',
    disabledInEditableMode: false,
    events: {
        "show.bs.offcanvas #top_menu_collapse, #top_menu_collapse_mobile": "_onCollapseShow",
        "hidden.bs.offcanvas #top_menu_collapse, #top_menu_collapse_mobile": "_onCollapseHidden",
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCollapseShow() {
        this.options.wysiwyg?.odooEditor.observerUnactive("addCollapseClass");
        this.el.classList.add('o_top_menu_collapse_shown');
        this.options.wysiwyg?.odooEditor.observerActive("addCollapseClass");
    },
    /**
     * @private
     */
    _onCollapseHidden() {
        this.options.wysiwyg?.odooEditor.observerUnactive("removeCollapseClass");
        const mobileNavbarEl = this.el.querySelector("#top_menu_collapse_mobile");
        if (!mobileNavbarEl.matches(".show, .showing")) {
            this.el.classList.remove("o_top_menu_collapse_shown");
        }
        this.options.wysiwyg?.odooEditor.observerActive("removeCollapseClass");
    },
});

publicWidget.registry.SearchModal = publicWidget.Widget.extend({
    selector: "#o_search_modal_block #o_search_modal",
    disabledInEditableMode: false,
    events: {
        "show.bs.modal": "_onSearchModalShow",
        "shown.bs.modal": "_onSearchModalShown",
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSearchModalShow(ev) {
        if (this.editableMode) {
            ev.preventDefault();
        }
    },
    /**
     * @private
     */
    _onSearchModalShown(ev) {
        this.el.querySelector(".search-query").focus();
    },
});

export default {
    extraMenuUpdateCallbacks: extraMenuUpdateCallbacks,
};
