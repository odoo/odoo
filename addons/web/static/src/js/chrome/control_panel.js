odoo.define('web.ControlPanelMixin', function (require) {
"use strict";

/**
 * Mixin allowing widgets to communicate with the ControlPanel. Widgets needing a
 * ControlPanel should use this mixin and call update_control_panel(cp_status) where
 * cp_status contains information for the ControlPanel to update itself.
 */
var ControlPanelMixin = {
    need_control_panel: true,
    /**
     * @param {web.Bus} [cp_bus] Bus to communicate with the ControlPanel
     */
    set_cp_bus: function(cp_bus) {
        this.cp_bus = cp_bus;
    },
    /**
     * Triggers 'update' on the cp_bus to update the ControlPanel according to cp_status
     * @param {Object} [cp_status] see web.ControlPanel.update() for a description
     * @param {Object} [options] see web.ControlPanel.update() for a description
     */
    update_control_panel: function(cp_status, options) {
        this.cp_bus.trigger("update", cp_status || {}, options || {});
    },
};

return ControlPanelMixin;

});

odoo.define('web.ControlPanel', function (require) {
"use strict";

var Bus = require('web.Bus');
var data = require('web.data');
var Widget = require('web.Widget');

var ControlPanel = Widget.extend({
    template: 'ControlPanel',
    /**
     * @param {String} [template] the QWeb template to render the ControlPanel.
     * By default, the template 'ControlPanel' will be used
     */
    init: function(parent, template) {
        this._super(parent);
        if (template) {
            this.template = template;
        }

        this.bus = new Bus();
        this.bus.on("update", this, this.update);
    },
    /**
     * Renders the control panel and creates a dictionnary of its exposed elements
     * @return {jQuery.Deferred}
     */
    start: function() {
        // Exposed jQuery nodesets
        this.nodes = {
            $breadcrumbs: this.$('.breadcrumb'),
            $buttons: this.$('.o_cp_buttons'),
            $pager: this.$('.o_cp_pager'),
            $searchview: this.$('.o_cp_searchview'),
            $searchview_buttons: this.$('.o_search_options'),
            $sidebar: this.$('.o_cp_sidebar'),
            $switch_buttons: this.$('.o_cp_switch_buttons'),
        };

        // Prevent the search dropdowns to close when clicking inside them
        this.$el.on('click.bs.dropdown', '.o_search_options .dropdown-menu', function (e) {
            e.stopPropagation();
        });

        // By default, hide the ControlPanel and remove its contents from the DOM
        this._toggle_visibility(false);

        return this._super();
    },
    destroy: function() {
        this._clear_breadcrumbs_handlers();
        return this._super.apply(this, arguments);
    },
    /**
     * @return {Object} the Bus the ControlPanel is listening on
     */
    get_bus: function() {
        return this.bus;
    },
    /**
     * Updates the content and displays the ControlPanel
     * @param {Object} [status.active_view] the current active view
     * @param {Array} [status.breadcrumbs] the breadcrumbs to display (see _render_breadcrumbs() for
     * precise description)
     * @param {Object} [status.cp_content] dictionnary containing the new ControlPanel jQuery elements
     * @param {Boolean} [status.hidden] true if the ControlPanel should be hidden
     * @param {openerp.web.SearchView} [status.searchview] the searchview widget
     * @param {Boolean} [status.search_view_hidden] true if the searchview is hidden, false otherwise
     * @param {Boolean} [options.clear] set to true to clear from control panel
     * elements that are not in status.cp_content
     */
    update: function(status, options) {
        this._toggle_visibility(!status.hidden);

        // Don't update the ControlPanel in headless mode as the views have
        // inserted themselves the buttons where they want, so inserting them
        // again in the ControlPanel will remove them from where they should be
        if (!status.hidden) {
            options = _.defaults({}, options, {
                clear: true, // clear control panel by default
            });
            var new_cp_content = status.cp_content || {};

            // Render the breadcrumbs
            if (status.breadcrumbs) {
                this._clear_breadcrumbs_handlers();
                this.$breadcrumbs = this._render_breadcrumbs(status.breadcrumbs);
                new_cp_content.$breadcrumbs = this.$breadcrumbs;
            }

            // Detach control_panel old content and attach new elements
            if (options.clear) {
                this._detach_content(this.nodes);
                // Show the searchview buttons area, which might have been hidden by
                // the searchview, as client actions may insert elements into it
                this.nodes.$searchview_buttons.show();
            } else {
                this._detach_content(_.pick(this.nodes, _.keys(new_cp_content)));
            }
            this._attach_content(new_cp_content);

            // Update the searchview and switch buttons
            this._update_search_view(status.searchview, status.search_view_hidden);
            if (status.active_view_selector) {
                this._update_switch_buttons(status.active_view_selector);
            }
        }
    },
    /**
     * Private function that hides (or shows) the ControlPanel in headless (resp. non-headless) mode
     * Also detaches or attaches its contents to clean the DOM
     * @param {Boolean} [visible] true to show the control panel, false to hide it
     */
    _toggle_visibility: function(visible) {
        this.do_toggle(visible);
        if (!visible && !this.$content) {
            this.$content = this.$el.contents().detach();
        } else if (this.$content) {
            this.$content.appendTo(this.$el);
            this.$content = null;
        }
    },
    /**
     * Private function that detaches the content of the ControlPanel
     * @param {Object} [elements_to_detach] subset of this.nodes to detach
     */
    _detach_content: function(elements_to_detach) {
        _.each(elements_to_detach, function($nodeset) {
            $nodeset.contents().detach();
        });
    },
    /**
     * Private function that attaches content to the ControlPanel
     * @param {Object} [content] dictionnary of jQuery elements to attach, whose keys
     * are jQuery nodes identifiers in this.nodes
     */
    _attach_content: function(content) {
        var self = this;
        _.each(content, function($nodeset, $element) {
            if ($nodeset && self.nodes[$element]) {
                self.nodes[$element].append($nodeset);
            }
        });
    },
    /**
     * Private function that removes active class on all switch-buttons and adds
     * it to the one of the active view
     * @param {Object} [active_view_selector] the selector of the div to activate
     */
    _update_switch_buttons: function(active_view_selector) {
        _.each(this.nodes.$switch_buttons.find('button'), function(button) {
            $(button).removeClass('active');
        });
        this.$(active_view_selector).addClass('active');
    },
    /**
     * Private function that renders the breadcrumbs
     * @param {Array} [breadcrumbs] list of objects containing the following keys:
     *      - action: the action to execute when clicking on this part of the breadcrumbs
     *      - index: the index in the breadcrumbs (starting at 0)
     *      - title: what to display in the breadcrumbs
     * @return {Array} list of breadcrumbs' li jQuery elements
     */
    _render_breadcrumbs: function (breadcrumbs) {
        var self = this;
        return breadcrumbs.map(function (bc, index) {
            return self._render_breadcrumbs_li(bc, index, breadcrumbs.length);
        });
    },
    /**
     * Private function that renders a breadcrumbs' li Jquery element
     */
    _render_breadcrumbs_li: function (bc, index, length) {
        var self = this;
        var is_last = (index === length-1);
        var li_content = bc.title && _.escape(bc.title.trim()) || data.noDisplayContent;
        var $bc = $('<li>')
            .append(is_last ? li_content : $('<a>').html(li_content))
            .toggleClass('active', is_last);
        if (!is_last) {
            $bc.click(function () {
                self.trigger("on_breadcrumb_click", bc.action, bc.index);
            });
        }
        return $bc;
    },
    /**
     * Private function that removes event handlers attached on the currently
     * displayed breadcrumbs.
     */
    _clear_breadcrumbs_handlers: function () {
        if (this.$breadcrumbs) {
            _.each(this.$breadcrumbs, function ($bc) {
                $bc.off();
            });
        }
    },
    /**
     * Private function that updates the SearchView's visibility and extend the
     * breadcrumbs area if the SearchView is not visible
     * @param {openerp.web.SearchView} [searchview] the searchview Widget
     * @param {Boolean} [is_hidden] visibility of the searchview
     */
    _update_search_view: function(searchview, is_hidden) {
        if (searchview) {
            // Set the $buttons div (in the DOM) of the searchview as the $buttons
            // have been appended to a jQuery node not in the DOM at SearchView initialization
            searchview.$buttons = this.nodes.$searchview_buttons;
            searchview.toggle_visibility(!is_hidden);
        }

        this.nodes.$searchview.toggle(!is_hidden);
        this.$el.toggleClass('o_breadcrumb_full', !!is_hidden);
    },
});

return ControlPanel;

});
