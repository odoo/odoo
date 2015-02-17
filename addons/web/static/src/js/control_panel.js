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
        this.bus.on("render_switch_buttons", this, this.render_switch_buttons);
        this.bus.on("update", this, this.update);
        this.bus.on("update_breadcrumbs", this, this.update_breadcrumbs);

        this.state = null;
        this.searchview = null;
    },
    start: function() {
        // Retrieve ControlPanel jQuery nodes
        this.$title_col = this.$('.oe-cp-title');
        this.$breadcrumbs = this.$('.oe-view-title');
        this.$searchview = this.$('.oe-cp-search-view');
        this.$searchview_buttons = this.$('.oe-search-options');
        this.$buttons = this.$('.oe-cp-buttons');
        this.$sidebar = this.$('.oe-cp-sidebar');
        this.$pager = this.$('.oe-cp-pager');
        this.$switch_buttons = this.$('.oe-cp-switch-buttons');

        // By default, hide the ControlPanel and remove its contents from the DOM
        this.$el.hide();
        this.contents = this.$el.contents().detach();

        return this._super();
    },
    /**
     * @return {Object} the Bus the ControlPanel is listening on
     */
    get_bus: function() {
        return this.bus;
    },
    /**
     * @return {Object} the current State of the ControlPanel
     */
    get_state: function() {
        return this.state;
    },
    /**
     * Sets the state of the controlpanel (in the case of a viewmanager, set_state must be
     * called before switch_mode for the controlpanel and the viewmanager to be synchronized)
     * @param {Object} [state] the new state
     */
    set_state: function(state) {
        this.state = state;
        // Set the new state searchview
        this.searchview = state.get_searchview();
    },
    /**
     * Returns the content of the ControlPanel without detaching anything from it
     * @return {Object} dictionnary containing the detached jQuery elements
     */
    get_content: function() {
        return {
            '$buttons': this.$buttons.contents(),
            '$switch_buttons': this.$switch_buttons.contents(),
            '$pager': this.$pager.contents(),
            '$sidebar': this.$sidebar.contents(),
            '$searchview': this.$searchview.contents(),
            '$searchview_buttons': this.$searchview_buttons.contents(),
        };
    },
    /**
     * Hides (or shows) the ControlPanel in headless (resp. non-headless) mode
     * Also detaches or attaches its contents to clean the DOM
     */
    toggle_visibility: function(hidden) {
        this.$el.toggle(!hidden);
        if (hidden && !this.contents) {
            this.contents = this.$el.contents().detach();
        } else if (this.contents) {
            this.contents.appendTo(this.$el);
            this.contents = null;
        }
    },
    /**
     * Detaches the content of the ControlPanel
     * @return {Object} dictionnary containing the detached jQuery elements
     */
    _detach_content: function() {
        var cp_content = this.get_content();
        _.each(cp_content, function($content) {
            $content.detach();
        });

        return cp_content;
    },
    /**
     * Attaches content to the ControlPanel
     * @param {Object} [content] dictionnary of jQuery elements to attach, whose keys
     * are jQuery nodes identifiers
     */
    _attach_content: function(content) {
        var self = this;
        _.each(content, function($nodeset, $element) {
            if ($nodeset && self[$element]) {
                $nodeset.appendTo(self[$element]);
            }
        });
    },
    /**
     * Updates the content and display of the ControlPanel
     * @param {Object} [status.active_view] the current active view
     * @param {Array} [status.breadcrumbs] the breadcrumbs to display
     * @param {Object} [status.cp_content] dictionnary containing the new ControlPanel jQuery elements
     * @param {Boolean} [status.hidden] true if the ControlPanel should be hidden
     * @param {openerp.web.SearchView} [status.searchview] the searchview widget
     * @param {Boolean} [status.search_view_hidden] true if the searchview is hidden, false otherwise
     */
    update: function(status) {
        this.toggle_visibility(status.hidden);
        if (!status.hidden) {
            // Don't update the ControlPanel in headless mode as the views have
            // inserted themselves the buttons where they want, so inserting them
            // again in the ControlPanel will removed them from there they should be
            this._detach_content();
            this._attach_content(status.cp_content);
            if (status.active_view) this.update_switch_buttons(status.active_view);
            if (status.searchview) this.update_search_view(status.searchview, status.search_view_hidden);
            if (status.breadcrumbs) this.update_breadcrumbs(status.breadcrumbs);
        }
    },
    /**
     * Renders the switch buttons and call set_switch_buttons on the src
     * Does not append the switch buttons to the DOM
     * @param {Object} [src] the source requesting the switch_buttons
     * @param {Array} [views] the array of views
     */
    render_switch_buttons: function(src, views) {
        if (views.length > 1) {
            var self = this;

            // Render switch buttons but do not append them to the DOM as this will
            // be done later, simultaneously to all other ControlPanel elements
            var $switch_buttons = $(QWeb.render('ControlPanel.switch-buttons', {views: views}));

            // Create bootstrap tooltips
            _.each(views, function(view) {
                self.$('.oe-cp-switch-' + view.type).tooltip();
            });
        }

        // Set the buttons jQuery elements in the Widget which made the request
        src.set_switch_buttons($switch_buttons);
    },
    /**
     * Triggers an event when switch-buttons are clicked on
     */
    on_switch_buttons_click: function(event) {
        var view_type = $(event.target).data('view-type');
        this.trigger('switch_view', view_type);
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
            $buttons: $("<div>"),
            action: action,
        };

        // Instantiate the SearchView, but do not append it nor its buttons to the DOM as this will
        // be done later, simultaneously to all other ControlPanel elements
        var searchview = new SearchView(this, dataset, view_id, search_defaults, options);
        searchview.appendTo($("<div>")).then(function() {
            // Set the SearchView in the widget which made the request
            src.set_search_view(searchview);
        });
    },
    /**
     * Updates the SearchView's visibility and extend the breadcrumbs area if the SearchView is not visible
     * @param {openerp.web.SearchView} [searchview] the searchview Widget
     * @param {Boolean} [is_hidden] visibility of the searchview
     **/
    update_search_view: function(searchview, is_hidden) {
        // Set the $buttons div (in the DOM) of the searchview as the $buttons
        // have been appended to a jQuery node not in the DOM at SearchView initialization
        searchview.$buttons = this.$searchview_buttons;
        searchview.toggle_visibility(!is_hidden);
        this.$title_col.toggleClass('col-md-6', !is_hidden).toggleClass('col-md-12', is_hidden);
    },
});

return ControlPanel;

});
