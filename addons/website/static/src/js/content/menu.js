odoo.define('website.content.menu', function (require) {
'use strict';

const config = require('web.config');
var dom = require('web.dom');
var publicWidget = require('web.public.widget');
var wUtils = require('website.utils');
var animations = require('website.content.snippets.animation');

const extraMenuUpdateCallbacks = [];

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
    },
    /**
     * @override
     */
    start: function () {
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
        this.$el.on('odoo-transitionstart.BaseAnimatedHeader', () => this._adaptToHeaderChangeLoop(1));
        this.$el.on('transitionend.BaseAnimatedHeader', () => this._adaptToHeaderChangeLoop(-1));

        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._toggleFixedHeader(false);
        this.$el.removeClass('o_header_affixed o_header_is_scrolled o_header_no_transition');
        this.$navbarCollapses.off('.BaseAnimatedHeader');
        this.$el.off('.BaseAnimatedHeader');
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptFixedHeaderPosition() {
        dom.compensateScrollbar(this.el, this.fixedHeader, false, 'right');
    },
    /**
     * @private
     */
    _adaptToHeaderChange: function () {
        this._updateMainPaddingTop();
        this.el.classList.toggle('o_top_fixed_element', this.fixedHeader && this._isShown());

        for (const callback of extraMenuUpdateCallbacks) {
            callback();
        }
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
        }

        // Indicates the page is scrolled, the logo size is changed.
        const headerIsScrolled = (scroll > this.scrolledPoint);
        if (this.headerIsScrolled !== headerIsScrolled) {
            this.el.classList.toggle('o_header_is_scrolled', headerIsScrolled);
            this.$el.trigger('odoo-transitionstart');
            this.headerIsScrolled = headerIsScrolled;
        }

        // Close opened menus
        this.$dropdowns.removeClass('show');
        this.$navbarCollapses.removeClass('show').attr('aria-expanded', false);
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
     * @private
     * @param {integer} scroll
     */
    _updateHeaderOnScroll: function (scroll) {
        this._super(...arguments);

        const mainPosScrolled = (scroll > this.headerHeight + this.topGap);
        const reachPosScrolled = (scroll > this.scrolledPoint + this.topGap);

        // Switch between static/fixed position of the header
        if (this.fixedHeader !== mainPosScrolled) {
            this.$el.css('transform', mainPosScrolled ? 'translate(0, -100%)' : '');
            void this.$el[0].offsetWidth; // Force a paint refresh
            this._toggleFixedHeader(mainPosScrolled);
        }
        // Show/hide header
        if (this.fixedHeaderShow !== reachPosScrolled) {
            this.$el.css('transform', reachPosScrolled ? `translate(0, -${this.topGap}px)` : 'translate(0, -100%)');
            this.fixedHeaderShow = reachPosScrolled;
            this._adaptToHeaderChange();
        }
    },
});

publicWidget.registry.FixedHeader = BaseAnimatedHeader.extend({
    selector: 'header.o_header_fixed',

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
    selector: 'header.o_header_disappears',

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
    selector: 'header.o_header_fade_out',

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
 * Auto adapt the header layout so that elements are not wrapped on a new line.
 */
publicWidget.registry.autohideMenu = publicWidget.Widget.extend({
    selector: 'header#top',
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.$topMenu = this.$('#top_menu');
        this.noAutohide = this.$el.is('.o_no_autohide_menu');
        if (!this.noAutohide) {
            await wUtils.onceAllImagesLoaded(this.$('.navbar'), this.$('.o_mega_menu, .o_offcanvas_logo_container, .dropdown-menu .o_lang_flag'));

            // The previous code will make sure we wait for images to be fully
            // loaded before initializing the auto more menu. But in some cases,
            // it is not enough, we also have to wait for fonts or even extra
            // scripts. Those will have no impact on the feature in most cases
            // though, so we will only update the auto more menu at that time,
            // no wait for it to initialize the feature.
            var $window = $(window);
            $window.on('load.autohideMenu', function () {
                $window.trigger('resize');
            });

            dom.initAutoMoreMenu(this.$topMenu, {unfoldable: '.divider, .divider ~ li, .o_no_autohide_item'});
        }
        this.$topMenu.removeClass('o_menu_loading');
        this.$topMenu.trigger('menu_loaded');
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        if (!this.noAutohide) {
            $(window).off('.autohideMenu');
            dom.destroyAutoMoreMenu(this.$topMenu);
        }
    },
});

/**
 * Note: this works well with the affixMenu... by chance (menuDirection is
 * called after alphabetically).
 *
 * @todo check bootstrap v4: maybe handled automatically now ?
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
        this.defaultAlignment = this.$el.is('.ml-auto, .ml-auto ~ *') ? 'right' : 'left';
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} alignment - either 'left' or 'right'
     * @param {integer} liOffset
     * @param {integer} liWidth
     * @param {integer} menuWidth
     * @param {integer} pageWidth
     * @returns {boolean}
     */
    _checkOpening: function (alignment, liOffset, liWidth, menuWidth, pageWidth) {
        if (alignment === 'left') {
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
        var $li = $(ev.target);
        var $menu = $li.children('.dropdown-menu');
        var liOffset = $li.offset().left;
        var liWidth = $li.outerWidth();
        var menuWidth = $menu.outerWidth();
        var pageWidth = $('#wrapwrap').outerWidth();

        $menu.removeClass('dropdown-menu-left dropdown-menu-right');

        var alignment = this.defaultAlignment;
        if ($li.nextAll(':visible').length === 0) {
            // The dropdown is the last menu item, open to the left
            alignment = 'right';
        }

        // If can't open in the current direction because it would overflow the
        // page, change the direction. But if the other direction would do the
        // same, change back the direction.
        for (var i = 0; i < 2; i++) {
            if (!this._checkOpening(alignment, liOffset, liWidth, menuWidth, pageWidth)) {
                alignment = (alignment === 'left' ? 'right' : 'left');
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
        if (config.device.size_class > config.device.SIZES.SM) {
            this.$dropdownMenus.css('margin-top', '0');
            this.$dropdownMenus.css('top', 'unset');
        } else {
            this.$dropdownMenus.css('margin-top', '');
            this.$dropdownMenus.css('top', '');
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
        if (config.device.size_class <= config.device.SIZES.SM) {
            return;
        }

        const $dropdown = $(ev.currentTarget);
        $dropdown.addClass('show');
        $dropdown.find(this.$dropdownToggles).attr('aria-expanded', 'true');
        $dropdown.find(this.$dropdownMenus).addClass('show');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseLeave: function (ev) {
        if (config.device.size_class <= config.device.SIZES.SM) {
            return;
        }

        const $dropdown = $(ev.currentTarget);
        $dropdown.removeClass('show');
        $dropdown.find(this.$dropdownToggles).attr('aria-expanded', 'false');
        $dropdown.find(this.$dropdownMenus).removeClass('show');
    },
});

publicWidget.registry.HeaderMainCollapse = publicWidget.Widget.extend({
    selector: 'header#top',
    events: {
        'show.bs.collapse #top_menu_collapse': '_onCollapseShow',
        'hidden.bs.collapse #top_menu_collapse': '_onCollapseHidden',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCollapseShow() {
        this.el.classList.add('o_top_menu_collapse_shown');
    },
    /**
     * @private
     */
    _onCollapseHidden() {
        this.el.classList.remove('o_top_menu_collapse_shown');
    },
});

return {
    extraMenuUpdateCallbacks: extraMenuUpdateCallbacks,
};
});
