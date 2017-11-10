odoo.define('website.content.menu', function (require) {
'use strict';

var config = require('web.config');
var sAnimation = require('website.content.snippets.animation');

sAnimation.registry.affixMenu = sAnimation.Class.extend({
    selector: 'header.o_affix_enabled',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }

        var self = this;
        this.$headerClone = this.$target.clone().addClass('o_header_affix affix').removeClass('o_affix_enabled');
        this.$headerClone.insertAfter(this.$target);
        this.$headers = this.$target.add(this.$headerClone);
        this.$dropdowns = this.$headers.find('.dropdown');
        this.$navbarCollapses = this.$headers.find('.navbar-collapse');

        // Handle events for the collapse menus
        _.each(this.$headerClone.find('[data-toggle="collapse"]'), function (el) {
            var $source = $(el);
            var targetClass = $source.attr('data-target');
            var $target = self.$headerClone.find(targetClass);
            var className = targetClass.substring(1);
            $source.attr('data-target', targetClass + '_clone');
            $target.removeClass(className).addClass(className + '_clone');
        });

        // Window Handlers
        $(window).on('resize.affixMenu scroll.affixMenu', _.throttle(this._onWindowUpdate.bind(this), 200));
        setTimeout(this._onWindowUpdate.bind(this), 0); // setTimeout to allow override with advanced stuff... see themes

        return def;
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
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the window is resized or scrolled -> updates affix status and
     * automatically closes submenus.
     *
     * @private
     */
    _onWindowUpdate: function () {
        var wOffset = $(window).scrollTop();
        var hOffset = this.$target.scrollTop();
        this.$headerClone.toggleClass('affixed', wOffset > (hOffset + 300));

        // Reset opened menus
        this.$dropdowns.removeClass('open');
        this.$navbarCollapses.removeClass('in').attr('aria-expanded', false);
    },
});

/**
 * Auto adapt the header layout so that elements are not wrapped on a new line.
 *
 * Note: this works well with the affixMenu... by chance (autohideMenu is called
 * after alphabetically).
 *
 * @todo We may want to avoid some code duplication by sharing what is done in
 * the backend in enterprise...
 */
sAnimation.registry.autohideMenu = sAnimation.Class.extend({
    selector: 'header:not(.o_no_autohide_menu) > .navbar > *',

    /**
     * @override
     */
    start: function () {
        this.$topMenu = this.$('#top_menu');
        this.$items = this.$topMenu.children();

        $(window).on('resize', _.debounce(this._adapt.bind(this), 500));
        this._adapt();

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this._restore();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adapt: function () {
        this._restore();
        if (config.device.size_class < config.device.SIZES.SM) {
            return;
        }

        this.maxWidth = this.$el.width();
        this.maxWidth -= _.reduce(this.$el.children().not('.navbar-collapse'), function (sum, el) {
            return sum + $(el).outerWidth(true);
        }, 0);

        var nbItems = this.$items.length;
        var menuItemsWidth = _.reduce(this.$items, function (sum, el) {
            return sum + $(el).outerWidth(true);
        }, 0);

        if (menuItemsWidth > this.maxWidth) {
            this.$extraItemsToggle = $('<li/>', {class: 'o_extra_menu_items'});
            this.$extraItemsToggle.append($('<a/>', {href: '#', class: 'dropdown-toggle', 'data-toggle': 'dropdown'})
                .append($('<i/>', {class: 'fa fa-plus'})));
            this.$extraItemsToggle.append($('<ul/>', {class: 'dropdown-menu'}));
            this.$extraItemsToggle.appendTo(this.$topMenu);

            menuItemsWidth += this.$extraItemsToggle.outerWidth(true);
            do {
                menuItemsWidth -= this.$items.eq(--nbItems).outerWidth(true);
            } while (menuItemsWidth > this.maxWidth);

            var $extraItems = this.$items.slice(nbItems).detach();
            this.$extraItemsToggle.children('ul').append($extraItems);
            this.$extraItemsToggle.toggleClass('active', $extraItems.hasClass('active'));
        }
    },
    /**
     * @private
     */
    _restore: function () {
        if (this.$extraItemsToggle) {
            this.$extraItemsToggle.find("> ul > *").appendTo(this.$topMenu);
            this.$extraItemsToggle.remove();
            delete this.$extraItemsToggle;
        }
    },
});

/**
 * Note: this works well with the affixMenu... by chance (menuDirection is
 * called after alphabetically).
 *
 * @todo check bootstrap v4: maybe handled automatically now ?
 */
sAnimation.registry.menuDirection = sAnimation.Class.extend({
    selector: 'header .navbar .nav',
    events: {
        'show.bs.dropdown': '_onDropdownShow',
    },

    /**
     * @override
     */
    start: function () {
        this.defaultAlignment = this.$el.is('.navbar-right') ? 'right' : 'left';
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
