odoo.define('web.ControlPanel', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var formats = require('web.formats');
var framework = require('web.framework');
var SearchView = require('web.SearchView');
var utils = require('web.utils');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var ControlPanel = Widget.extend({
    template: 'ControlPanel',
    events: {
        "click .oe_debug_view": "on_debug_changed",
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
        this.dataset = null;
        this.active_view = null;
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
    // Sets the state of the controlpanel (in the case of a viewmanager, set_state must be
    // called before switch_mode for the controlpanel and the viewmanager to be synchronized)
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
        this.active_view = state.widget.active_view;
        this.dataset = state.widget.dataset;
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
        this.active_view = active_view; // this.active_view only used for debug view

        this.update_switch_buttons(active_view);
        this.update_search_view(search_view_hidden);
        this.update_breadcrumbs(breadcrumbs);
        this.render_debug_view();
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
    on_debug_changed: function (evt) {
        var self = this,
            params = $(evt.target).data(),
            val = params.action,
            current_view = this.active_view.controller;
        switch (val) {
            case 'fvg':
                var dialog = new Dialog(this, { title: _t("Fields View Get") }).open();
                $('<pre>').text(utils.json_node_to_xml(current_view.fields_view.arch, true)).appendTo(dialog.$el);
                break;
            case 'tests':
                this.do_action({
                    name: _t("JS Tests"),
                    target: 'new',
                    type : 'ir.actions.act_url',
                    url: '/web/tests?mod=*'
                });
                break;
            case 'get_metadata':
                var ids = current_view.get_selected_ids();
                if (ids.length === 1) {
                    this.dataset.call('get_metadata', [ids]).done(function(result) {
                        new Dialog(this, {
                            title: _.str.sprintf(_t("Metadata (%s)"), self.dataset.model),
                            size: 'medium',
                            buttons: {
                                Ok: function() { this.parents('.modal').modal('hide');}
                            },
                        }, QWeb.render('ViewManagerDebugViewLog', {
                            perm : result[0],
                            format : formats.format_value
                        })).open();
                    });
                }
                break;
            case 'toggle_layout_outline':
                current_view.rendering_engine.toggle_layout_debugging();
                break;
            case 'set_defaults':
                current_view.open_defaults_dialog();
                break;
            case 'translate':
                this.do_action({
                    name: _t("Technical Translation"),
                    res_model : 'ir.translation',
                    domain : [['type', '!=', 'object'], '|', ['name', '=', this.dataset.model], ['name', 'ilike', this.dataset.model + ',']],
                    views: [[false, 'list'], [false, 'form']],
                    type : 'ir.actions.act_window',
                    view_type : "list",
                    view_mode : "list"
                });
                break;
            case 'fields':
                this.dataset.call('fields_get', [false, {}]).done(function (fields) {
                    var $root = $('<dl>');
                    _(fields).each(function (attributes, name) {
                        $root.append($('<dt>').append($('<h4>').text(name)));
                        var $attrs = $('<dl>').appendTo($('<dd>').appendTo($root));
                        _(attributes).each(function (def, name) {
                            if (def instanceof Object) {
                                def = JSON.stringify(def);
                            }
                            $attrs
                                .append($('<dt>').text(name))
                                .append($('<dd style="white-space: pre-wrap;">').text(def));
                        });
                    });
                    new Dialog(self, {
                        title: _.str.sprintf(_t("Model %s fields"),
                                             self.dataset.model),
                        buttons: {
                            Ok: function() { this.parents('.modal').modal('hide');}
                        },
                        }, $root).open();
                });
                break;
            case 'edit_workflow':
                return this.do_action({
                    res_model : 'workflow',
                    name: _t('Edit Workflow'),
                    domain : [['osv', '=', this.dataset.model]],
                    views: [[false, 'list'], [false, 'form'], [false, 'diagram']],
                    type : 'ir.actions.act_window',
                    view_type : 'list',
                    view_mode : 'list'
                });
            case 'edit':
                this.do_edit_resource(params.model, params.id, evt.target.text);
                break;
            case 'manage_filters':
                this.do_action({
                    res_model: 'ir.filters',
                    name: _t('Manage Filters'),
                    views: [[false, 'list'], [false, 'form']],
                    type: 'ir.actions.act_window',
                    context: {
                        search_default_my_filters: true,
                        search_default_model_id: this.dataset.model
                    }
                });
                break;
            case 'print_workflow':
                if (current_view.get_selected_ids  && current_view.get_selected_ids().length == 1) {
                    framework.blockUI();
                    var action = {
                        context: { active_ids: current_view.get_selected_ids() },
                        report_name: "workflow.instance.graph",
                        datas: {
                            model: this.dataset.model,
                            id: current_view.get_selected_ids()[0],
                            nested: true,
                        }
                    };
                    this.session.get_file({
                        url: '/web/report',
                        data: {action: JSON.stringify(action)},
                        complete: framework.unblockUI
                    });
                } else {
                    self.do_warn("Warning", "No record selected.");
                }
                break;
            case 'leave_debug':
                window.location.search="?";
                break;
            default:
                if (val) {
                    console.warn("No debug handler for ", val);
                }
        }
    },
    do_edit_resource: function(model, id, name) {
        this.do_action({
            res_model : model,
            res_id : id,
            name: name,
            type : 'ir.actions.act_window',
            view_type : 'form',
            view_mode : 'form',
            views : [[false, 'form']],
            target : 'new',
            flags : {
                action_buttons : true,
                headless: true,
            }
        });
    },
    /**
     * Renders the debug dropdown according to the active_view
     */
    render_debug_view: function() {
        var self = this;
        if (self.session.debug) {
            self.$('.oe_debug_view').html(QWeb.render('ViewManagerDebug', {
                view: self.active_view.controller,
                widget: self,
            }));
        }
    },
});

return ControlPanel;

});
