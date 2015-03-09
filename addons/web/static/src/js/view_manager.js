odoo.define('web.ViewManager', ['web.core', 'web.data', 'web.Dialog', 'web.formats', 'web.framework', 'web.Model', 'web.pyeval', 'web.utils', 'web.SearchView', 'web.session', 'web.Widget'], function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var formats = require('web.formats');
var framework = require('web.framework');
var Model = require('web.Model');
var pyeval = require('web.pyeval');
var utils = require('web.utils');
var SearchView = require('web.SearchView');
var session = require('web.session');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

var ViewManager = Widget.extend({
    template: "ViewManager",
    /**
     * @param {Object} [dataset] null object (... historical reasons)
     * @param {Array} [views] List of [view_id, view_type]
     * @param {Object} [flags] various boolean describing UI state
     */
    init: function(parent, dataset, views, flags, action) {
        if (action) {
            flags = action.flags || {};
            if (!('auto_search' in flags)) {
                flags.auto_search = action.auto_search !== false;
            }
            if (action.res_model === 'board.board' && action.view_mode === 'form') {
                action.target = 'inline';
                // Special case for Dashboards
                _.extend(flags, {
                    views_switcher : false,
                    display_title : false,
                    search_view : false,
                    pager : false,
                    sidebar : false,
                    action_buttons : false
                });
            }
            this.action = action;
            this.action_manager = parent;
            this.debug = session.debug;
            dataset = new data.DataSetSearch(this, action.res_model, action.context, action.domain);
            if (action.res_id) {
                dataset.ids.push(action.res_id);
                dataset.index = 0;
            }
            views = action.views;
        }
        var self = this;
        this._super(parent);

        this.flags = flags || {};
        this.dataset = dataset;
        this.view_order = [];
        this.url_states = {};
        this.views = {};
        this.view_stack = []; // used for breadcrumbs
        this.active_view = null;
        this.searchview = null;
        this.active_search = null;
        this.registry = core.view_registry;
        this.title = this.action && this.action.name;

        _.each(views, function (view) {
            var view_type = view[1] || view.view_type,
                View = core.view_registry.get(view_type, true),
                view_label = View ? View.prototype.display_name: (void 'nope'),
                view_descr = {
                    controller: null,
                    options: view.options || {},
                    view_id: view[0] || view.view_id,
                    type: view_type,
                    label: view_label,
                    embedded_view: view.embedded_view,
                    title: self.action && self.action.name,
                    button_label: View ? _.str.sprintf(_t('%(view_type)s view'), {'view_type': (view_label || view_type)}) : (void 'nope'),
                };
            self.view_order.push(view_descr);
            self.views[view_type] = view_descr;
        });
        this.multiple_views = (self.view_order.length > 1);
    },
    /**
     * @returns {jQuery.Deferred} initial view loading promise
     */
    start: function() {
        var self = this;
        var default_view = this.flags.default_view || this.view_order[0].type,
            default_options = this.flags[default_view] && this.flags[default_view].options;

        if (this.flags.headless) {
            this.$('.oe-view-manager-header').hide();
        }
        this._super();
        var $sidebar = this.flags.sidebar ? this.$('.oe-view-manager-sidebar') : undefined,
            $pager = this.$('.oe-view-manager-pager');

        this.$breadcrumbs = this.$('.oe-view-title');
        this.$switch_buttons = this.$('.oe-view-manager-switch button');
        this.$header = this.$('.oe-view-manager-header');
        this.$header_col = this.$header.find('.oe-header-title');
        this.$search_col = this.$header.find('.oe-view-manager-search-view');
        this.$switch_buttons.click(function (event) {
            var view_type = $(this).data('view-type');
            if ((view_type === 'form') && (self.active_view.type === 'form')) {
                self._display_view(view_type);
            } else {
                self.switch_mode(view_type);
            }
        });
        var views_ids = {};
        _.each(this.views, function (view) {
            views_ids[view.type] = view.view_id;
            view.options = _.extend({
                $buttons: self.$('.oe-' + view.type + '-buttons'),
                $sidebar : $sidebar,
                $pager : $pager,
                action : self.action,
                action_views_ids : views_ids,
            }, self.flags, self.flags[view.type], view.options);
            view.$container = self.$(".oe-view-manager-view-" + view.type);

            // show options.$buttons as views will put their $buttons inside it
            // and call show/hide on them
            view.options.$buttons.show();
            self.$('.oe-vm-switch-' + view.type).tooltip();
        });
        this.$('.oe_debug_view').click(this.on_debug_changed);
        this.$el.addClass("oe_view_manager_" + ((this.action && this.action.target) || 'current'));

        this.search_view_loaded = this.setup_search_view();
        var main_view_loaded = this.switch_mode(default_view, null, default_options);

        return $.when(main_view_loaded, this.search_view_loaded);
    },

    switch_mode: function(view_type, no_store, view_options) {
        var self = this,
            view = this.views[view_type];

        if (!view) {
            return $.Deferred().reject();
        }
        if ((view_type !== 'form') && (view_type !== 'diagram')) {
            this.view_stack = [];
        } 
        this.view_stack.push(view);

        // Hide active view (at first rendering, there is no view to hide)
        if (this.active_view && this.active_view !== view) {
            if (this.active_view.controller) this.active_view.controller.do_hide();
            if (this.active_view.$container) this.active_view.$container.hide();
        }
        this.active_view = view;

        if (!view.created) {
            view.created = this.create_view.bind(this)(view, view_options);
        }
        this.active_search = $.Deferred();

        if (this.searchview && 
                this.flags.auto_search && 
                view.controller.searchable !== false) {
            $.when(this.search_view_loaded, view.created).done(this.searchview.do_search);
        } else {
            this.active_search.resolve();
        }

        self.update_header();
        return $.when(view.created, this.active_search).done(function () {
            self.active_view = view;
            self._display_view(view_options);
            self.trigger('switch_mode', view_type, no_store, view_options);
            if (self.debug) {
                self.$('.oe_debug_view').html(QWeb.render('ViewManagerDebug', {
                    view: self.active_view.controller,
                    view_manager: self,
                    uid: session.uid,
                }));
            }
        });
    },
    update_header: function () {
        this.$switch_buttons.removeClass('active');
        this.$('.oe-vm-switch-' + this.active_view.type).addClass('active');
    },
    _display_view: function (view_options) {
        var self = this;
        this.active_view.$container.show();
        $.when(this.active_view.controller.do_show(view_options)).done(function () {
            if (self.searchview) {
                var is_hidden = self.active_view.controller.searchable === false;
                self.searchview.toggle_visibility(!is_hidden);
                self.$header_col.toggleClass('col-md-6', !is_hidden).toggleClass('col-md-12', is_hidden);
                self.$search_col.toggle(!is_hidden);
            }
            self.display_breadcrumbs();
        });
    },
    display_breadcrumbs: function () {
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
    create_view: function(view, view_options) {
        var self = this,
            View = this.registry.get(view.type),
            options = _.clone(view.options),
            view_loaded = $.Deferred();

        if (view.type === "form" && ((this.action && (this.action.target === 'new' || this.action.target === 'inline'))
                || (view_options && view_options.mode === 'edit'))) {
            options.initial_mode = 'edit';
        }
        var controller = new View(this, this.dataset, view.view_id, options),
            $container = view.$container;

        $container.hide();
        view.controller = controller;
        view.$container = $container;

        if (view.embedded_view) {
            controller.set_embedded_view(view.embedded_view);
        }
        controller.on('switch_mode', this, this.switch_mode.bind(this));
        controller.on('history_back', this, function () {
            if (self.action_manager) self.action_manager.trigger('history_back');
        });
        controller.on("change:title", this, function() {
            self.display_breadcrumbs();
        });
        controller.on('view_loaded', this, function () {
            view_loaded.resolve();
        });
        this.$('.oe-view-manager-pager > span').hide();
        return $.when(controller.appendTo($container), view_loaded)
                .done(function () { 
                    self.trigger("controller_inited", view.type, controller);
                });
    },
    select_view: function (index) {
        var view_type = this.view_stack[index].type;
        this.view_stack.splice(index);
        return this.switch_mode(view_type);
    },
    /**
     * @returns {Number|Boolean} the view id of the given type, false if not found
     */
    get_view_id: function(view_type) {
        return this.views[view_type] && this.views[view_type].view_id || false;
    },
    /**
     * Sets up the current viewmanager's search view.
     *
     * @param {Number|false} view_id the view to use or false for a default one
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
        return this.searchview.appendTo(this.$(".oe-view-manager-search-view:first"));
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
            var groupby = results.group_by.length
                        ? results.group_by
                        : action_context.group_by;
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
    do_push_state: function(state) {
        if (this.action_manager) {
            state.view_type = this.active_view.type;
            this.action_manager.do_push_state(state);
        }
    },
    do_load_state: function(state, warm) {
        if (state.view_type && state.view_type !== this.active_view.type) {
            // warning: this code relies on the fact that switch_mode has an immediate side
            // effect (setting the 'active_view' to its new value) AND an async effect (the
            // view is created/loaded).  So, the next statement (do_load_state) is executed 
            // on the new view, after it was initialized, but before it is fully loaded and 
            // in particular, before the do_show method is called.
            this.switch_mode(state.view_type, true);
        } 
        this.active_view.controller.do_load_state(state, warm);
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
                        }));
                        dialog.open();
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
});

return ViewManager;

});
