odoo.define('web.ControlPanel', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');
var formats = require('web.formats');
var framework = require('web.framework');
var Model = require('web.Model');
var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');
var utils = require('web.utils');
var Widget = require('web.Widget');

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

        this.view_manager = parent;
        this.action_manager = this.view_manager.action_manager;
        this.action = this.view_manager.action;
        this.dataset = this.view_manager.dataset;
        this.active_view = this.view_manager.active_view;
        this.views = this.view_manager.views;
        this.flags = this.view_manager.flags;
        this.title = this.view_manager.title; // needed for Favorites of searchview
        this.view_order = this.view_manager.view_order;
        this.multiple_views = (this.view_order.length > 1);
    },
    start: function() {
        var self = this;

        // Retrieve control panel elements
        this.$control_panel = this.$('.oe-control-panel-content');
        this.$breadcrumbs = this.$('.oe-view-title');
        this.$switch_buttons = this.$('.oe-cp-switch-buttons button');
        this.$title_col = this.$control_panel.find('.oe-cp-title');
        this.$search_col = this.$control_panel.find('.oe-cp-search-view');
        // AAB: Use sidebar and pager of the ControlPanel only if it is displayed, otherwise set them
        // to undefined to that the view uses its own elements to sidebar and pager, as follows:
        // this.$sidebar = !this.flags.headless && this.flags.sidebar ? this.$('.oe-cp-sidebar') : undefined,
        // this.$pager = !this.flags.headless ? this.$('.oe-cp-pager') : undefined;
        // But rather use the following definition to keep behavior as it is for now (i.e. it does not
        // display the pager in one2many list views)
        this.$sidebar = this.flags.sidebar ? this.$('.oe-cp-sidebar') : undefined;
        this.$pager = this.$('.oe-cp-pager');

        // Hide the ControlPanel in headless mode
        if (this.flags.headless) {
            this.$control_panel.hide();
        }

        _.each(this.views, function (view) {
            // Expose control panel elements to the views so that they can insert stuff in them
            view.options = _.extend(view.options, {
                $buttons : !self.flags.headless ? self.$('.oe-' + view.type + '-buttons') : undefined,
                $sidebar : self.$sidebar,
                $pager : self.$pager,
            }, self.flags, self.flags[view.type], view.options);
            // Show $buttons as views will put their own buttons inside it and show/hide them
            if (view.options.$buttons) view.options.$buttons.show();
            self.$('.oe-cp-switch-' + view.type).tooltip();
        });

        // Create the searchview
        this.search_view_loaded = this.setup_search_view();

        return this._super();
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
     */
    update: function(active_view) {
        this.active_view = active_view;

        this.update_search_view();
        this.update_breadcrumbs();
        this.render_debug_view();

        // Update switch-buttons
        this.$switch_buttons.removeClass('active');
        this.$('.oe-cp-switch-' + this.active_view.type).addClass('active');
    },
    update_breadcrumbs: function () {
        var self = this;
        if (!this.action_manager) return;
        var breadcrumbs = this.action_manager.get_breadcrumbs();
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
                    self.action_manager.select_widget(bc.widget, bc.index);
                });
            }
            return $bc;
        }
    },
    /**
     * Sets up the search view.
     *
     * @returns {jQuery.Deferred} search view startup deferred
     */
    setup_search_view: function() {
        if (this.searchview) {
            this.searchview.destroy();
        }

        var view_id = (this.action && this.action.search_view_id && this.action.search_view_id[0]) || false;

        var search_defaults = {};

        var context = this.action ? this.action.context : [];
        _.each(context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                search_defaults[match[1]] = value;
            }
        });

        var options = {
            hidden: this.flags.search_view === false,
            disable_custom_filters: this.flags.search_disable_custom_filters,
            $buttons: this.$('.oe-search-options'),
            action: this.action,
        };
        this.searchview = new SearchView(this, this.dataset, view_id, search_defaults, options);

        this.searchview.on('search_data', this, this.search.bind(this));
        return this.searchview.appendTo(this.$(".oe-cp-search-view:first"));
    },
    update_search_view: function() {
        if (this.searchview) {
            var is_hidden = this.active_view.controller.searchable === false;
            this.searchview.toggle_visibility(!is_hidden);
            this.$title_col.toggleClass('col-md-6', !is_hidden).toggleClass('col-md-12', is_hidden);
            this.$search_col.toggle(!is_hidden);
        }
    },
    search: function(domains, contexts, groupbys) {
        var self = this,
            controller = this.active_view.controller,
            action_context = this.action.context || {},
            view_context = controller.get_context();
        pyeval.eval_domains_and_contexts({
            domains: [this.action.domain || []].concat(domains || []),
            contexts: [action_context, view_context].concat(contexts || []),
            group_by_seq: groupbys || []
        }).done(function (results) {
            if (results.error) {
                self.active_search.resolve();
                throw new Error(
                        _.str.sprintf(_t("Failed to evaluate search criterions")+": \n%s",
                                      JSON.stringify(results.error)));
            }
            self.dataset._model = new Model(
                self.dataset.model, results.context, results.domain);
            var groupby = results.group_by.length ?
                          results.group_by :
                          action_context.group_by;
            if (_.isString(groupby)) {
                groupby = [groupby];
            }
            if (!controller.grouped && !_.isEmpty(groupby)){
                self.dataset.set_sort([]);
            }
            $.when(controller.do_search(results.domain, results.context, groupby || [])).then(function() {
                self.active_search.resolve();
            });
        });
    },
    activate_search: function(view_created_def) {
        this.active_search = $.Deferred();
        if (this.searchview &&
                this.flags.auto_search &&
                this.active_view.controller.searchable !== false) {
            $.when(this.search_view_loaded,view_created_def).done(this.searchview.do_search);
        } else {
            this.active_search.resolve();
        }
        return this.active_search;
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
                        var dialog = new Dialog(this, {
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
