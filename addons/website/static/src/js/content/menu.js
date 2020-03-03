odoo.define('website.content.menu', function (require) {
'use strict';

const config = require('web.config');
var dom = require('web.dom');
var publicWidget = require('web.public.widget');
var wUtils = require('website.utils');
var animations = require('website.content.snippets.animation');

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
        this.$el.on('odoo-transitionstart.BaseAnimatedHeader', () => this._updateMainPaddingTopLoop(1));
        this.$el.on('transitionend.BaseAnimatedHeader', () => this._updateMainPaddingTopLoop(-1));

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
     * @param {boolean} [useFixed=true]
     */
    _toggleFixedHeader: function (useFixed = true) {
        this.fixedHeader = useFixed;
        this.el.classList.toggle('o_header_affixed', useFixed);
        this._updateMainPaddingTop();
    },
    /**
     * @private
     */
    _updateMainPaddingTop: function () {
        this.headerHeight = this.$el.outerHeight();
        if (this.isOverlayHeader) {
            return;
        }
        const headerSize = this.el.classList.contains('o_header_affixed');
        this.$main.css('padding-top', headerSize ? this.headerHeight : '');
    },
    /**
     * @private
     * @param {integer} [addCount=0]
     */
    _updateMainPaddingTopLoop: function (addCount = 0) {
        this._updateMainPaddingTop();

        this._transitionCount += addCount;
        this._transitionCount = Math.max(0, this._transitionCount);

        // The normal case would be to have the transitionend event to be
        // fired but we cannot rely on it, so we use a timeout as fallback.
        clearTimeout(this._paddingLoopTimer);
        if (this._transitionCount > 0) {
            window.requestAnimationFrame(() => this._updateMainPaddingTopLoop());
            this._paddingLoopTimer = setTimeout(() => this._updateMainPaddingTopLoop(-1), 500);
        }
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

        // Reset opened menus
        if (this.$navbarCollapses.hasClass('show')) {
            return;
        }
        this.$dropdowns.removeClass('show');
        this.$navbarCollapses.removeClass('show').attr('aria-expanded', false);
    },
    /**
     * Called when the window is resized
     *
     * @private
     */
    _updateHeaderOnResize: function () {
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
     * Called when the window is scrolled
     *
     * @private
     * @param {integer} scroll
     */
    _updateHeaderOnScroll: function (scroll) {
        this._super(...arguments);

        const mainPosScrolled = (scroll > this.headerHeight);
        const reachPosScrolled = (scroll > this.scrolledPoint);

        // Switch between static/fixed position of the header
        if (this.fixedHeader !== mainPosScrolled) {
            this.$el.css('transform', mainPosScrolled ? 'translate(0, -100%)' : '');
            void this.$el[0].offsetWidth; // Force a paint refresh
            this._toggleFixedHeader(mainPosScrolled);
        }
        // Show/hide header
        if (this.fixedHeaderShow !== reachPosScrolled) {
            this.$el.css('transform', reachPosScrolled ? '' : 'translate(0, -100%)');
            this.fixedHeaderShow = reachPosScrolled;
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
        if (scroll > this.scrolledPoint) {
            if (!this.$el.hasClass('o_header_affixed')) {
                this._toggleFixedHeader(true);
            }
        } else {
            this._toggleFixedHeader(false);
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
        this.checkPoint = 0;
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
     * @abstract
     */
    _hideHeader: function () {},
    /**
     * @private
     */
    _showHeader: function () {},

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateHeaderOnScroll: function (scroll) {
        this._super(...arguments);

        const scrollingDownwards = (scroll > this.position);
        if (scrollingDownwards !== this.scrollingDownwards) {
            this.checkPoint = scroll;
        }

        if (scrollingDownwards) {
            if (!this.hiddenHeader && scroll - this.checkPoint > 200) {
                this.hiddenHeader = true;
                this._hideHeader();
            }
        } else {
            if (this.hiddenHeader && scroll - this.checkPoint < -100) {
                this.hiddenHeader = false;
                this._showHeader();
            }
        }

        this.scrollingDownwards = scrollingDownwards;
        this.position = scroll;
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
        this.$el.css('transform', 'translate(0, -100%)');
    },
    /**
     * @override
     */
    _showHeader: function () {
        this.$el.css('transform', '');
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
        this.$el.stop(false, true).fadeOut();
    },
    /**
     * @override
     */
    _showHeader: function () {
        this.$el.stop(false, true).fadeIn();
    },
});

/**
 * Auto adapt the header layout so that elements are not wrapped on a new line.
 */
publicWidget.registry.autohideMenu = publicWidget.Widget.extend({
    selector: 'header #top_menu',

    /**
     * @override
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        this.noAutohide = this.$el.closest('.o_no_autohide_menu').length;
        if (!this.noAutohide) {
            var $navbar = this.$el.closest('.navbar');
            defs.push(wUtils.onceAllImagesLoaded($navbar));

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
        }
        return Promise.all(defs).then(function () {
            if (!self.noAutohide) {
                dom.initAutoMoreMenu(self.$el, {unfoldable: '.divider, .divider ~ li'});
            }
            self.$el.removeClass('o_menu_loading');
            self.$el.trigger('menu_loaded');
        });
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        if (!this.noAutohide) {
            $(window).off('.autohideMenu');
            dom.destroyAutoMoreMenu(this.$el);
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
     * @returns {boolean}
     */
    _checkOpening: function (alignment, liOffset, liWidth, menuWidth, windowWidth) {
        if (alignment === 'left') {
            // Check if ok to open the dropdown to the right (no window overflow)
            return (liOffset + menuWidth <= windowWidth);
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
        var windowWidth = $(window).outerWidth();

        $menu.removeClass('dropdown-menu-left dropdown-menu-right');

        var alignment = this.defaultAlignment;
        if ($li.nextAll(':visible').length === 0) {
            // The dropdown is the last menu item, open to the left
            alignment = 'right';
        }

        // If can't open in the current direction because it would overflow the
        // window, change the direction. But if the other direction would do the
        // same, change back the direction.
        for (var i = 0; i < 2; i++) {
            if (!this._checkOpening(alignment, liOffset, liWidth, menuWidth, windowWidth)) {
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
        'mouseenter .dropdown:not(.position-static)': '_onMouseEnter',
        'mouseleave .dropdown:not(.position-static)': '_onMouseLeave',
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
});
