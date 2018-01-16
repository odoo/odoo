odoo.define('web.Menu', function (require) {
"use strict";

var core = require('web.core');
var session = require('web.session');
var Widget = require('web.Widget');

var Menu = Widget.extend({
    init: function() {
        this._super.apply(this, arguments);
        this.is_bound = $.Deferred();
        this.data = {data:{children:[]}};
        core.bus.on('change_menu_section', this, this.on_change_top_menu);
    },
    start: function() {
        this._super.apply(this, arguments);
        return this.bind_menu();
    },
    do_reload: function() {
        var self = this;
        self.bind_menu();
    },
    bind_menu: function() {
        var self = this;
        this.$secondary_menus = this.$el.parents().find('.o_sub_menu');
        this.$secondary_menus.on('click', 'a[data-menu]', this.on_menu_click);
        this.$el.on('click', 'a[data-menu]', function (event) {
            event.preventDefault();
            var menu_id = $(event.currentTarget).data('menu');
            core.bus.trigger('change_menu_section', menu_id);
        });

        // Hide second level submenus
        this.$secondary_menus.find('.oe_menu_toggler').siblings('.oe_secondary_submenu').addClass('o_hidden');
        if (self.current_menu) {
            self.open_menu(self.current_menu);
        }
        this.trigger('menu_bound');

        var lazyreflow = _.debounce(this.reflow.bind(this), 200);
        core.bus.on('resize', this, function() {
            if ($(window).width() < 768 ) {
                lazyreflow('all_outside');
            } else {
                lazyreflow();
            }
        });
        core.bus.trigger('resize');

        this.is_bound.resolve();
    },

    /**
     * Reflow the menu items and dock overflowing items into a "More" menu item.
     * Automatically called when 'menu_bound' event is triggered and on window resizing.
     *
     * @param {string} behavior If set to 'all_outside', all the items are displayed.
     * If not set, only the overflowing items are hidden.
     */
    reflow: function(behavior) {
        var self = this;
        var $more_container = this.$('#menu_more_container').hide();
        var $more = this.$('#menu_more');
        var $systray = this.$el.parents().find('.oe_systray');

        $more.children('li').insertBefore($more_container);  // Pull all the items out of the more menu

        // 'all_outside' beahavior should display all the items, so hide the more menu and exit
        if (behavior === 'all_outside') {
            // Show list of menu items
            self.$el.show();
            this.$el.find('li').show();
            $more_container.hide();
            return;
        }

        // Hide all menu items
        var $toplevel_items = this.$el.find('li').not($more_container).not($systray.find('li')).hide();
        // Show list of menu items (which is empty for now since all menu items are hidden)
        self.$el.show();
        $toplevel_items.each(function() {
            var remaining_space = self.$el.parent().width() - $more_container.outerWidth();
            self.$el.parent().children(':visible').each(function() {
                remaining_space -= $(this).outerWidth();
            });

            if ($(this).width() >= remaining_space) {
                return false; // the current item will be appended in more_container
            }
            $(this).show(); // show the current item in menu bar
        });
        $more.append($toplevel_items.filter(':hidden').show());
        $more_container.toggle(!!$more.children().length);
        // Hide toplevel item if there is only one
        var $toplevel = self.$el.children("li:visible");
        if ($toplevel.length === 1) {
            $toplevel.hide();
        }
    },
    /**
     * Opens a given menu by id, as if a user had browsed to that menu by hand
     * except does not trigger any event on the way
     *
     * @param {Number} id database id of the terminal menu to select
     */
    open_menu: function (id) {
        this.current_menu = id;
        session.active_id = id;
        var $clicked_menu, $sub_menu, $main_menu;
        $clicked_menu = this.$el.add(this.$secondary_menus).find('a[data-menu=' + id + ']');
        this.trigger('open_menu', id, $clicked_menu);

        if (this.$secondary_menus.has($clicked_menu).length) {
            $sub_menu = $clicked_menu.parents('.oe_secondary_menu');
            $main_menu = this.$el.find('a[data-menu=' + $sub_menu.data('menu-parent') + ']');
        } else {
            $sub_menu = this.$secondary_menus.find('.oe_secondary_menu[data-menu-parent=' + $clicked_menu.attr('data-menu') + ']');
            $main_menu = $clicked_menu;
        }

        this.current_primary_menu = $main_menu.data('menu');

        // Activate current main menu
        this.$el.find('.active').removeClass('active');
        $main_menu.parent().addClass('active');

        // Show current sub menu
        this.$secondary_menus.find('.oe_secondary_menu').hide();
        $sub_menu.show();

        // Hide/Show the leftbar menu depending of the presence of sub-items
        this.$secondary_menus.toggleClass('o_hidden', !$sub_menu.children().length);

        // Activate current menu item and show parents
        this.$secondary_menus.find('.active').removeClass('active');
        if ($main_menu !== $clicked_menu) {
            $clicked_menu.parents().removeClass('o_hidden');
            if ($clicked_menu.is('.oe_menu_toggler')) {
                $clicked_menu.toggleClass('oe_menu_opened').siblings('.oe_secondary_submenu:first').toggleClass('o_hidden');
            } else {
                $clicked_menu.parent().addClass('active');
            }
        }
        // add a tooltip to cropped menu items
        this.$secondary_menus.find('.oe_secondary_submenu li a span').each(function() {
            $(this).tooltip(this.scrollWidth > this.clientWidth ? {title: $(this).text().trim(), placement: 'right'} :'destroy');
       });
    },
    /**
     * Call open_menu with the first menu_item matching an action_id
     *
     * @param {Number} id the action_id to match
     */
    open_action: function (id) {
        var $menu = this.$el.add(this.$secondary_menus).find('a[data-action-id="' + id + '"]');
        var menu_id = $menu.data('menu');
        if (menu_id) {
            this.open_menu(menu_id);
        }
    },
    /**
     * Process a click on a menu item
     *
     * @param {Number} id the menu_id
     */
    menu_click: function(id) {
        if (!id) { return; }

        // find back the menuitem in dom to get the action
        var $item = this.$el.find('a[data-menu=' + id + ']');
        if (!$item.length) {
            $item = this.$secondary_menus.find('a[data-menu=' + id + ']');
        }
        var action_id = $item.data('action-id');
        // If first level menu doesnt have action trigger first leaf
        if (!action_id) {
            if(this.$el.has($item).length) {
                var $sub_menu = this.$secondary_menus.find('.oe_secondary_menu[data-menu-parent=' + id + ']');
                var $items = $sub_menu.find('a[data-action-id]').filter('[data-action-id!=""]');
                if($items.length) {
                    action_id = $items.data('action-id');
                    id = $items.data('menu');
                }
            }
        }
        if (action_id) {
            this.trigger('menu_click', {
                action_id: action_id,
                id: id,
                previous_menu_id: this.current_menu // Here we don't know if action will fail (in which case we have to revert menu)
            }, $item);
        } else {
            console.log('Menu no action found web test 04 will fail');
        }
        this.open_menu(id);
    },

    /**
     * Change the current top menu
     *
     * @param {int} [menu_id] the top menu id
     */
    on_change_top_menu: function(menu_id) {
        var self = this;
        this.menu_click(menu_id);
    },
    on_menu_click: function(ev) {
        ev.preventDefault();
        this.menu_click($(ev.currentTarget).data('menu'));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the id of the current primary (first level) menu.
     *
     * @returns {integer}
     */
    getCurrentPrimaryMenu: function () {
        return this.current_primary_menu;
    },
});

return Menu;
});
