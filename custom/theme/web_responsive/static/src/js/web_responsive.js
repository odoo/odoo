/* Copyright 2016 LasLabs Inc.
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

odoo.define('web_responsive', function(require) {
    'use strict';

    var Menu = require('web.Menu');
    var Class = require('web.Class');
    var SearchView = require('web.SearchView');
    var core = require('web.core');

    Menu.include({

        // Force all_outside to prevent app icons from going into more menu
        reflow: function() {
            this._super('all_outside');
        },

        /* Overload to collapse unwanted visible submenus
         * @param allow_open bool Switch to allow submenus to be opened
         */
        open_menu: function(id, allowOpen) {
            this._super(id);
            if (allowOpen) return;
            var $clicked_menu = this.$secondary_menus.find('a[data-menu=' + id + ']');
            $clicked_menu.parents('.oe_secondary_submenu').css('display', '');
        },

    });

    SearchView.include({

        // Prevent focus of search field on mobile devices
        toggle_visibility: function (is_visible) {
            $('div.oe_searchview_input').last()
                .one('focus', $.proxy(this.preventMobileFocus, this));
            return this._super(is_visible);
        },

        // It prevents focusing of search el on mobile
        preventMobileFocus: function(event) {
            if (this.isMobile()) {
                event.preventDefault();
            }
        },

        // For lack of Modernizr, TouchEvent will do
        isMobile: function () {
            try{
                document.createEvent('TouchEvent');
                return true;
            } catch (ex) {
                return false;
            }
        },

    });

    var AppDrawer = Class.extend({

        LEFT: 'left',
        RIGHT: 'right',
        UP: 'up',
        DOWN: 'down',

        isOpen: false,
        keyBuffer: '',
        keyBufferTime: 500,
        keyBufferTimeoutEvent: false,
        dropdownHeightFactor: 0.90,
        initialized: false,

        init: function() {
            this.directionCodes = {
                'left': this.LEFT,
                'right': this.RIGHT,
                'up': this.UP,
                'pageup': this.UP,
                'down': this.DOWN,
                'pagedown': this.DOWN,
                '+': this.RIGHT,
                '-': this.LEFT,
            };
            this.initDrawer();
            var $clickZones = $('.odoo_webclient_container, ' +
                                'a.oe_menu_leaf, ' +
                                'a.oe_menu_toggler, ' +
                                'a.oe_logo, ' +
                                'i.oe_logo_edit'
                                );
            $clickZones.click($.proxy(this.handleClickZones, this));
            core.bus.on('resize', this, this.handleWindowResize);
            core.bus.on('keydown', this, this.handleNavKeys);
        },

        // It provides initialization handlers for Drawer
        initDrawer: function() {
            this.$el = $('.drawer');
            this.$el.drawer();
            this.$el.one('drawer.opened', $.proxy(this.onDrawerOpen, this));
            this.$el.on('drawer.opened', function setIScrollProbes(){
                var onIScroll = function() {
                    var transform = (this.iScroll.y) ? this.iScroll.y * -1 : 0;
                    $(this).find('#appDrawerAppPanelHead').css(
                        'transform', 'matrix(1, 0, 0, 1, 0, ' + transform + ')'
                    );
                };
                this.iScroll.options.probeType = 2;
                this.iScroll.on('scroll', $.proxy(onIScroll, this));
            });
            this.initialized = true;
        },

        // It provides handlers to hide drawer when "unfocused"
        handleClickZones: function() {
            this.$el.drawer('close');
            $('.o_sub_menu_content')
                .parent()
                .collapse('hide');
        },

        // It resizes bootstrap dropdowns for screen
        handleWindowResize: function() {
            $('.dropdown-scrollable').css(
                'max-height', $(window).height() * this.dropdownHeightFactor
            );
        },

        // It provides keyboard shortcuts for app drawer nav
        handleNavKeys: function(e) {
            if (!this.isOpen){
                return;
            }
            var directionCode = $.hotkeys.specialKeys[e.keyCode.toString()];
            if (Object.keys(this.directionCodes).indexOf(directionCode) !== -1) {
                var $link = this.findAdjacentAppLink(
                    this.$el.find('a:first, a:focus').last(),
                    this.directionCodes[directionCode]
                );
                this.selectAppLink($link);
            } else if ($.hotkeys.specialKeys[e.keyCode.toString()] == 'esc') {
                this.handleClickZones();
            } else {
                var buffer = this.handleKeyBuffer(e.keyCode);
                this.selectAppLink(this.searchAppLinks(buffer));
            }
        },

        /* It adds to keybuffer, sets expire timer, and returns buffer
         * @returns str of current buffer
         */
        handleKeyBuffer: function(keyCode) {
            this.keyBuffer += String.fromCharCode(keyCode);
            if (this.keyBufferTimeoutEvent) {
                clearTimeout(this.keyBufferTimeoutEvent);
            }
            this.keyBufferTimeoutEvent = setTimeout(
                $.proxy(this.clearKeyBuffer, this),
                this.keyBufferTime
            );
            return this.keyBuffer;
        },

        clearKeyBuffer: function() {
            this.keyBuffer = '';
        },

        /* It performs close actions
         * @fires ``drawer.closed`` to the ``core.bus``
         * @listens ``drawer.opened`` and sends to onDrawerOpen
         */
        onDrawerClose: function() {
            core.bus.trigger('drawer.closed');
            this.$el.one('drawer.opened', $.proxy(this.onDrawerOpen, this));
            this.isOpen = false;
            // Remove inline style inserted by drawer.js
            this.$el.css("overflow", "");
        },

        /* It finds app links and register event handlers
         * @fires ``drawer.opened`` to the ``core.bus``
         * @listens ``drawer.closed`` and sends to :meth:``onDrawerClose``
         */
        onDrawerOpen: function() {
            this.$appLinks = $('.app-drawer-icon-app').parent();
            this.selectAppLink($(this.$appLinks[0]));
            this.$el.one('drawer.closed', $.proxy(this.onDrawerClose, this));
            core.bus.trigger('drawer.opened');
            this.isOpen = true;
        },

        // It selects an app link visibly
        selectAppLink: function($appLink) {
            if ($appLink) {
                $appLink.focus();
            }
        },

        /* It returns first App Link by its name according to query
         * @param query str to search
         * @return jQuery obj
         */
        searchAppLinks: function(query) {
            return this.$appLinks.filter(function() {
                return $(this).data('menuName').toUpperCase().startsWith(query);
            }).first();
        },

        /* It returns the link adjacent to $appLink in provided direction.
         * It also handles edge cases in the following ways:
         *   * Moves to last link if LEFT on first
         *   * Moves to first link if PREV on last
         *   * Moves to first link of following row if RIGHT on last in row
         *   * Moves to last link of previous row if LEFT on first in row
         *   * Moves to top link in same column if DOWN on bottom row
         *   * Moves to bottom link in same column if UP on top row
         * @param $appLink jQuery obj of App icon link
         * @param direction str of direction to go (constants LEFT, UP, etc.)
         * @return jQuery obj for adjacent applink
         */
        findAdjacentAppLink: function($appLink, direction) {

            var obj = [],
                $objs = this.$appLinks;

            switch(direction){
                case this.LEFT:
                    obj = $objs[$objs.index($appLink) - 1];
                    if (!obj) {
                        obj = $objs[$objs.length - 1];
                    }
                    break;
                case this.RIGHT:
                    obj = $objs[$objs.index($appLink) + 1];
                    if (!obj) {
                        obj = $objs[0];
                    }
                    break;
                case this.UP:
                    $objs = this.getRowObjs($appLink, this.$appLinks);
                    obj = $objs[$objs.index($appLink) - 1];
                    if (!obj) {
                        obj = $objs[$objs.length - 1];
                    }
                    break;
                case this.DOWN:
                    $objs = this.getRowObjs($appLink, this.$appLinks);
                    obj = $objs[$objs.index($appLink) + 1];
                    if (!obj) {
                        obj = $objs[0];
                    }
                    break;
            }

            if (obj.length) {
                event.preventDefault();
            }

            return $(obj);

        },

        /* It returns els in the same row
         * @param @obj jQuery object to get row for
         * @param $grid jQuery objects representing grid
         * @return $objs jQuery objects of row
         */
        getRowObjs: function($obj, $grid) {
            // Filter by object which middle lies within left/right bounds
            function filterWithin(left, right) {
                return function() {
                    var $this = $(this),
                        thisMiddle = $this.offset().left + ($this.width() / 2);
                    return thisMiddle >= left && thisMiddle <= right;
                };
            }
            var left = $obj.offset().left,
                right = left + $obj.outerWidth();
            return $grid.filter(filterWithin(left, right));
        },

    });

    // It inits a new AppDrawer when the web client is ready
    core.bus.on('web_client_ready', null, function () {
        new AppDrawer();
    });

    return {
        'AppDrawer': AppDrawer,
        'SearchView': SearchView,
        'Menu': Menu,
    };

});
