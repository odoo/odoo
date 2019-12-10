odoo.define('website.content.menu', function (require) {
'use strict';

var dom = require('web.dom');
var publicWidget = require('web.public.widget');
var wUtils = require('website.utils');

publicWidget.registry.affixMenu = publicWidget.Widget.extend({
    selector: 'header.o_affix_enabled',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        var self = this;
        this.$headerClone = this.$target.clone().addClass('o_header_affix affix').removeClass('o_affix_enabled').removeAttr('id');
        this.$headerClone.insertAfter(this.$target);
        this.$headers = this.$target.add(this.$headerClone);
        this.$dropdowns = this.$headers.find('.dropdown');
        this.$dropdownMenus = this.$headers.find('.dropdown-menu');
        this.$navbarCollapses = this.$headers.find('.navbar-collapse');

        this._adaptDefaultOffset();
        wUtils.onceAllImagesLoaded(this.$headerClone).then(function () {
            self._adaptDefaultOffset();
        });

        // Handle events for the collapse menus
        _.each(this.$headerClone.find('[data-toggle="collapse"]'), function (el) {
            var $source = $(el);
            var targetIDSelector = $source.attr('data-target');
            var $target = self.$headerClone.find(targetIDSelector);
            $source.attr('data-target', targetIDSelector + '_clone');
            $target.attr('id', targetIDSelector.substr(1) + '_clone');
        });
        // While scrolling through navbar menus, body should not be scrolled with it
        this.$headerClone.find('div.navbar-collapse').on('show.bs.collapse', function () {
            $(document.body).addClass('overflow-hidden');
        }).on('hide.bs.collapse', function () {
            $(document.body).removeClass('overflow-hidden');
        });

        // Window Handlers
        $(window).on('resize.affixMenu scroll.affixMenu', _.throttle(this._onWindowUpdate.bind(this), 200));
        setTimeout(this._onWindowUpdate.bind(this), 0); // setTimeout to allow override with advanced stuff... see themes

        return def.then(function () {
            self.trigger_up('widgets_start_request', {
                $target: self.$headerClone,
            });
        });
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$headerClone) {
            this.$headerClone.remove();
            $(window).off('.affixMenu');
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptDefaultOffset: function () {
        var bottom = this.$target.offset().top + this._getHeaderHeight();
        this.$headerClone.css('margin-top', Math.min(-200, -bottom) + 'px');
    },
    /**
     * @private
     */
    _getHeaderHeight: function () {
        return this.$headerClone.outerHeight();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the window is resized or scrolled -> updates affix status and
     * automatically closes submenus.
     *
     * @private
     */
    _onWindowUpdate: function () {
        if (this.$navbarCollapses.hasClass('show')) {
            return;
        }

        var wOffset = $(window).scrollTop();
        var hOffset = this.$target.scrollTop();
        this.$headerClone.toggleClass('affixed', wOffset > (hOffset + 300));

        // Reset opened menus
        this.$dropdowns.add(this.$dropdownMenus).removeClass('show');
        this.$navbarCollapses.removeClass('show').attr('aria-expanded', false);
    },
});

/**
 * Auto adapt the header layout so that elements are not wrapped on a new line.
 *
 * Note: this works well with the affixMenu... by chance (autohideMenu is called
 * after alphabetically).
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
        for (var i = 0 ; i < 2 ; i++) {
            if (!this._checkOpening(alignment, liOffset, liWidth, menuWidth, windowWidth)) {
                alignment = (alignment === 'left' ? 'right' : 'left');
            }
        }

        $menu.addClass('dropdown-menu-' + alignment);
    },
});
});
