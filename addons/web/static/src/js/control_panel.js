odoo.define('web.ControlPanel', function (require) {
"use strict";

var core = require('web.core');
var SearchView = require('web.SearchView');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var ControlPanel = Widget.extend({
    template: 'ControlPanel',
    events: {
        "click .oe-cp-switch-buttons button": "on_switch_buttons_click",
    },
    /**
     * @param {String} [template] the QWeb template to render the ControlPanel.
     * By default, the template 'ControlPanel' will be used
     */
    init: function(parent, template) {
        this._super(parent);
        if (template) {
            this.template = template;
        }

        this.bus = new core.Bus();
        this.bus.on("setup_search_view", this, this.setup_search_view);
        this.bus.on("update", this, this.update);
        this.bus.on("update_breadcrumbs", this, this.update_breadcrumbs);
        this.bus.on("render_buttons", this, this.render_buttons);
        this.bus.on("render_switch_buttons", this, this.render_switch_buttons);

        this.searchview = null;

        this.flags = null;
        this.title = null; // Needed for Favorites of searchview
    },
    start: function() {
        // Retrieve ControlPanel jQuery nodes
        this.$control_panel = this.$('.oe-control-panel-content');
        this.$breadcrumbs = this.$('.oe-view-title');
        this.$buttons = this.$('.oe-cp-buttons');
        this.$switch_buttons = this.$('.oe-cp-switch-buttons');
        this.$title_col = this.$control_panel.find('.oe-cp-title');
        this.$search_col = this.$control_panel.find('.oe-cp-search-view');
        this.$searchview = this.$(".oe-cp-search-view");
        this.$searchview_buttons = this.$('.oe-search-options');
        this.$pager = this.$('.oe-cp-pager');
        this.$sidebar = this.$('.oe-cp-sidebar');

        return this._super();
    },
    /**
     * @return {Object} Dictionnary of ControlPanel nodes
     */
    get_cp_nodes: function() {
        return {
            $buttons: this.$buttons,
            $switch_buttons: this.$switch_buttons,
            $sidebar: this.$sidebar,
            $pager: this.$pager
        };
    },
    get_bus: function() {
        return this.bus;
    },
    /**
     * Sets the state of the controlpanel (in the case of a viewmanager, set_state must be
     * called before switch_mode for the controlpanel and the viewmanager to be synchronized)
     */
    set_state: function(state, old_state) {
        // Detach control panel elements in which sub-elements are inserted by other widgets
        var old_content = {
            '$buttons': this.$buttons.contents().detach(),
            '$switch_buttons': this.$switch_buttons.contents().detach(),
            '$pager': this.$pager.contents().detach(),
            '$sidebar': this.$sidebar.contents().detach(),
            'searchview': this.searchview, // AAB: do better with searchview
            '$searchview': this.$searchview.contents().detach(),
            '$searchview_buttons': this.$searchview_buttons.contents().detach(),
        };
        if (old_state) {
            // Store them to re-attach them if we come back to that state (e.g. using breadcrumbs)
            old_state.set_cp_content(old_content);
        }

        this.state = state;
        this.flags = state.get_flags();

        this.flags = state.widget.flags;
        this.title = state.widget.title; // needed for Favorites of searchview

        // Hide the ControlPanel in headless mode
        this.$el.toggle(!this.flags.headless);

        var content = state.get_cp_content();
        if (content) {
            // This state has already been rendered once
            content.$buttons.appendTo(this.$buttons);
            content.$switch_buttons.appendTo(this.$switch_buttons);
            content.$pager.appendTo(this.$pager);
            content.$sidebar.appendTo(this.$sidebar);
            this.searchview = content.searchview;
            content.$searchview.appendTo(this.$searchview);
            content.$searchview_buttons.appendTo(this.$searchview_buttons);
        }
    },
    get_state: function() {
        return this.state;
    },
    render_buttons: function(views) {
        var self = this;

        var buttons_divs = QWeb.render('ControlPanel.buttons', {views: views});
        $(buttons_divs).appendTo(this.$buttons);

        // Show each div as views will put their own buttons inside it and show/hide them
        _.each(views, function(view) {
            self.$('.oe-' + view.type + '-buttons').show();
        });
    },
    render_switch_buttons: function(views) {
        if (views.length > 1) {
            var self = this;

            var switch_buttons = QWeb.render('ControlPanel.switch-buttons', {views: views});
            $(switch_buttons).appendTo(this.$switch_buttons);

            // Create tooltips
            _.each(views, function(view) {
                self.$('.oe-cp-switch-' + view.type).tooltip();
            });
        }
    },
     /**
     * Triggers an event when switch-buttons are clicked on
     */
    on_switch_buttons_click: function(event) {
        var view_type = $(event.target).data('view-type');
        this.trigger('switch_view', view_type);
    },
    /**
     * Updates its status according to the active_view
     * @param {Object} [active_view] the current active view
     * @param {Boolean} [search_view_hidden] true if the searchview is hidden, false otherwise
     * @param {Array} [breadcrumbs] the breadcrumbs to display
     */
    update: function(active_view, search_view_hidden, breadcrumbs) {
        this.update_switch_buttons(active_view);
        this.update_search_view(search_view_hidden);
        this.update_breadcrumbs(breadcrumbs);
    },
    /**
     * Removes active class on all switch-buttons and adds it to the one of the active view
     * @param {Object} [active_view] the active_view
     */
    update_switch_buttons: function(active_view) {
        _.each(this.$switch_buttons.contents('button'), function(button) {
            $(button).removeClass('active');
        });
        this.$('.oe-cp-switch-' + active_view.type).addClass('active');
    },
    /**
     * Updates the breadcrumbs
     **/
    update_breadcrumbs: function (breadcrumbs) {
        var self = this;

        if (!breadcrumbs.length) return;

        var $breadcrumbs = breadcrumbs.map(function (bc, index) {
            return make_breadcrumb(bc, index === breadcrumbs.length - 1);
        });

        this.$breadcrumbs
            .empty()
            .append($breadcrumbs);

        function make_breadcrumb (bc, is_last) {
            var $bc = $('<li>')
                    .append(is_last ? bc.title : $('<a>').text(bc.title))
                    .toggleClass('active', is_last);
            if (!is_last) {
                $bc.click(function () {
                    self.trigger("on_breadcrumb_click", bc.widget, bc.index);
                });
            }
            return $bc;
        }
    },
    /**
     * Sets up the search view and calls set_search_view on the widget requesting it
     *
     * @param {Object} [src] the widget requesting a search_view
     * @param {Object} [action] the action (required to instantiated the SearchView)
     * @param {Object} [dataset] the dataset (required to instantiated the SearchView)
     * @param {Object} [flags] a dictionnary of Booleans
     */
    setup_search_view: function(src, action, dataset, flags) {
        var self = this;
        var view_id = (action && action.search_view_id && action.search_view_id[0]) || false;

        var search_defaults = {};

        var context = action ? action.context : [];
        _.each(context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                search_defaults[match[1]] = value;
            }
        });

        var options = {
            hidden: flags.search_view === false,
            disable_custom_filters: flags.search_disable_custom_filters,
            $buttons: this.$searchview_buttons,
            action: action,
        };

        // Instantiate the SearchView and append it to the DOM
        this.searchview = new SearchView(this, dataset, view_id, search_defaults, options);
        var search_view_loaded = this.searchview.appendTo(this.$searchview);
        // Sets the SearchView in the widget which made the request
        src.set_search_view(self.searchview, search_view_loaded);
    },
    /**
     * Updates the SearchView's visibility and extend the breadcrumbs area if the SearchView is not visible
     * @param {Boolean} [is_hidden] visibility of the searchview
     **/
    update_search_view: function(is_hidden) {
        if (this.searchview) {
            this.searchview.toggle_visibility(!is_hidden);
            this.$title_col.toggleClass('col-md-6', !is_hidden).toggleClass('col-md-12', is_hidden);
            this.$search_col.toggle(!is_hidden);
        }
    },
});

return ControlPanel;

});
