odoo.define('web_kanban.KanbanView', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var data_manager = require('web.data_manager');
var Model = require('web.DataModel');
var Dialog = require('web.Dialog');
var form_common = require('web.form_common');
var Pager = require('web.Pager');
var pyeval = require('web.pyeval');
var QWeb = require('web.QWeb');
var session = require('web.session');
var utils = require('web.utils');
var View = require('web.View');

var KanbanColumn = require('web_kanban.Column');
var quick_create = require('web_kanban.quick_create');
var KanbanRecord = require('web_kanban.Record');
var kanban_widgets = require('web_kanban.widgets');

var qweb = core.qweb;
var _lt = core._lt;
var _t = core._t;
var ColumnQuickCreate = quick_create.ColumnQuickCreate;
var fields_registry = kanban_widgets.registry;

var KanbanView = View.extend({
    accesskey: "k",
    className: "o_kanban_view",
    custom_events: {
        'kanban_record_open': 'open_record',
        'kanban_record_edit': 'edit_record',
        'kanban_record_delete': 'delete_record',
        'kanban_do_action': 'open_action',
        'kanban_reload': 'do_reload',
        'kanban_column_resequence': function (event) {
            this.resequence_column(event.target);
        },
        'kanban_record_update': 'update_record',
        'kanban_column_add_record': 'add_record_to_column',
        'kanban_column_delete': 'delete_column',
        'kanban_column_archive_records': 'archive_records',
        'column_add_record': 'column_add_record',
        'quick_create_add_column': 'add_new_column',
        'kanban_load_more': 'load_more',
        'kanban_call_method': 'call_method',
    },
    defaults: _.extend(View.prototype.defaults, {
        quick_creatable: true,
        creatable: true,
        create_text: undefined,
        read_only_mode: false,
        confirm_on_delete: true,
    }),
    display_name: _lt("Kanban"),
    icon: 'fa-th-large',
    mobile_friendly: true,

    init: function () {
        this._super.apply(this, arguments);

        this.qweb = new QWeb(session.debug, {_s: session.origin});

        this.limit = this.options.limit || parseInt(this.fields_view.arch.attrs.limit, 10) || 40;
        this.fields = this.fields_view.fields;
        this.fields_keys = _.keys(this.fields_view.fields);
        this.grouped = undefined;
        this.group_by_field = undefined;
        this.default_group_by = this.fields_view.arch.attrs.default_group_by;
        this.on_create = this.fields_view.arch.attrs.on_create;
        this.grouped_by_m2o = undefined;
        this.relation = undefined;
        this.is_empty = undefined;
        // Retrieve many2manys stored in the fields_view if it has already been processed
        this.many2manys = this.fields_view.many2manys || [];
        this.m2m_context = {};
        this.widgets = [];
        this.data = undefined;
        this.quick_creatable = this.options.quick_creatable;
        this.no_content_msg = this.options.action &&
                              (this.options.action.get_empty_list_help || this.options.action.help);
        this.search_orderer = new utils.DropMisordered();

        // use default order if defined in xml description
        var default_order = this.fields_view.arch.attrs.default_order;
        if (!this.dataset._sort.length && default_order) {
            this.dataset.set_sort(default_order.split(','));
        }
    },

    willStart: function() {
        // add qweb templates
        for (var i=0, ii=this.fields_view.arch.children.length; i < ii; i++) {
            var child = this.fields_view.arch.children[i];
            if (child.tag === "templates") {
                transform_qweb_template(child, this.fields_view, this.many2manys);
                // transform_qweb_template(), among other things, identifies and processes the
                // many2manys. Unfortunately, it modifies the fields_view in place and, as
                // the fields_view is stored in the JS cache, the many2manys are only identified the
                // first time the fields_view is processed. We thus store the identified many2manys
                // on the fields_view, so that we can retrieve them later. A better fix would be to
                // stop modifying shared resources in place.
                this.fields_view.many2manys = this.many2manys;
                this.qweb.add_template(utils.json_node_to_xml(child));
                break;
            } else if (child.tag === 'field') {
                var ftype = child.attrs.widget || this.fields[child.attrs.name].type;
                if(ftype === "many2many" && "context" in child.attrs) {
                    this.m2m_context[child.attrs.name] = child.attrs.context;
                }
            }
        }
        return this._super();
    },

    start: function() {
        this.$el.addClass(this.fields_view.arch.attrs.class);
        return this._super();
    },

    do_search: function(domain, context, group_by) {
        var self = this;
        var group_by_field = group_by[0] || this.default_group_by;
        var field = this.fields[group_by_field];
        var options = {};
        var fields_def;
        if (field === undefined) {
            fields_def = data_manager.load_fields(this.dataset).then(function (fields) {
                self.fields = fields;
                field = self.fields[group_by_field];
            });
        }
        var load_def = $.when(fields_def).then(function() {
            var grouped_by_m2o = field && (field.type === 'many2one');
            options = _.extend(options, {
                search_domain: domain,
                search_context: context,
                group_by_field: group_by_field,
                grouped: group_by.length || self.default_group_by,
                grouped_by_m2o: grouped_by_m2o,
                relation: (grouped_by_m2o ? field.relation : undefined),
            });
            return options.grouped ? self.load_groups(options) : self.load_records();
        });
        return this.search_orderer
            .add(load_def)
            .then(function (data) {
                _.extend(self, options);
                if (options.grouped) {
                    var new_ids = _.union.apply(null, _.map(data.groups, function (group) {
                        return group.dataset.ids;
                    }));
                    self.dataset.alter_ids(new_ids);
                }
                self.data = data;
            })
            .then(this.proxy('render'))
            .then(this.proxy('update_buttons'))
            .then(this.proxy('update_pager'));
    },

    do_show: function() {
        this.do_push_state({});
        return this._super();
    },

    do_reload: function() {
        var group_by = this.group_by_field ? [this.group_by_field] : [];
        this.do_search(this.search_domain, this.search_context, group_by);
    },

    load_records: function (offset, dataset) {
        var options = {
            'limit': this.limit,
            'offset': offset,
        };
        dataset = dataset || this.dataset;
        return dataset
            .read_slice(this.fields_keys.concat(['__last_update']), options)
            .then(function(records) {
                return {
                    records: records,
                    is_empty: !records.length,
                    grouped: false,
                };
            });
    },

    load_groups: function (options) {
        var self = this;
        var group_by_field = options.group_by_field;
        var fields_keys = _.uniq(this.fields_keys.concat(group_by_field));

        return new Model(this.model, options.search_context, options.search_domain)
        .query(fields_keys)
        .group_by([group_by_field])
        .then(function (groups) {

            // Check in the arch the fields to fetch on the stage to get tooltips data.
            // Fetching data is done in batch for all stages, to avoid doing multiple
            // calls. The first naive implementation of group_by_tooltip made a call
            // for each displayed stage and was quite limited.
            // Data for the group tooltip (group_by_tooltip) and to display stage-related
            // legends for kanban state management (states_legend) are fetched in
            // one call.
            var group_by_fields_to_read = [];
            var group_options = {};
            var recurse = function(node) {
                if (node.tag === "field" && node.attrs && node.attrs.options && node.attrs.name === group_by_field) {
                    var options = pyeval.py_eval(node.attrs.options);
                    group_options = options;
                    var states_fields_to_read = _.map(
                        options && options.states_legend || {},
                        function (value, key, list) { return value; });
                    var tooltip_fields_to_read = _.map(
                        options && options.group_by_tooltip || {},
                        function (value, key, list) { return key; });
                    group_by_fields_to_read = _.union(
                        group_by_fields_to_read,
                        states_fields_to_read,
                        tooltip_fields_to_read);
                    return;
                }
                _.each(node.children, function(child) {
                    recurse(child);
                });
            };
            recurse(self.fields_view.arch);

            // fetch group data (display information)
            var group_ids = _.without(_.map(groups, function (elem) { return elem.attributes.value[0];}), undefined);
            if (options.grouped_by_m2o && group_ids.length && group_by_fields_to_read.length) {
                return new data.DataSet(self, options.relation)
                    .read_ids(group_ids, _.union(['display_name'], group_by_fields_to_read))
                    .then(function(results) {
                        _.each(groups, function (group) {
                            var group_id = group.attributes.value[0];
                            var result = _.find(results, function (data) {return group_id === data.id;});
                            group.title = result ? result.display_name : _t("Undefined");
                            group.values = result;
                            group.id = group_id;
                            group.options = group_options;
                        });
                        return groups;
                    });
            } else {
                _.each(groups, function (group) {
                    var value = group.attributes.value;
                    group.id = value instanceof Array ? value[0] : value;
                    var field = self.fields[options.group_by_field];
                    if (field && field.type === "selection") {
                        value= _.find(field.selection, function (s) { return s[0] === group.id; });
                    }
                    group.title = (value instanceof Array ? value[1] : value) || _t("Undefined");
                    group.values = {};
                });
                return $.when(groups);
            }
        })
        .then(function (groups) {
            var undef_index = _.findIndex(groups, function (g) { return g.title === _t("Undefined");});
            if (undef_index >= 1) {
                var undef_group = groups[undef_index];
                groups.splice(undef_index, 1);
                groups.unshift(undef_group);
            }
            return groups;
        })
        .then(function (groups) {
            // load records for each group
            var is_empty = true;
            return $.when.apply(null, _.map(groups, function (group) {
                var def = $.when([]);
                var dataset = new data.DataSetSearch(self, self.model,
                    new data.CompoundContext(self.dataset.get_context(), group.model.context()), group.model.domain());
                if (self.dataset._sort) {
                    dataset.set_sort(self.dataset._sort);
                }
                if (group.attributes.length >= 1) {
                    def = dataset.read_slice(self.fields_keys.concat(['__last_update']), { 'limit': self.limit });
                }
                return def.then(function (records) {
                    self.dataset.ids.push.apply(self.dataset.ids, _.difference(dataset.ids, self.dataset.ids));
                    group.records = records;
                    group.dataset = dataset;
                    is_empty = is_empty && !records.length;
                    return group;
                });
            })).then(function () {
                return {
                    groups: Array.prototype.slice.call(arguments, 0),
                    is_empty: is_empty,
                    grouped: true,
                };
            });
        });
    },

    is_action_enabled: function(action) {
        if (action === 'create' && !this.options.creatable) {
            return false;
        }
        return this._super(action);
    },
    has_active_field: function() {
        return this.fields_view.fields.active;
    },
    _is_quick_create_enabled: function() {
        var group_by_field = this.group_by_field.split(':')[0]
        if(!_.contains(['char', 'boolean', 'many2one'], this.fields[group_by_field].type)){
            return false;
        }
        if (!this.quick_creatable || !this.is_action_enabled('create'))
            return false;
        if (this.fields_view.arch.attrs.quick_create !== undefined)
            return JSON.parse(this.fields_view.arch.attrs.quick_create);
        return !!this.grouped;
    },
    /**
     * Render the buttons according to the KanbanView.buttons template and
     * add listeners on it.
     * Set this.$buttons with the produced jQuery element
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should be inserted
     * $node may be undefined, in which case the ListView inserts them into this.options.$buttons
     */
    render_buttons: function($node) {
        var self = this;
        if (this.options.action_buttons !== false && this.is_action_enabled('create')) {
            this.$buttons = $(qweb.render("KanbanView.buttons", {'widget': this}));
            this.$buttons.on('click', 'button.o-kanban-button-new', function () {
                if (self.grouped && self.widgets.length && self.on_create === 'quick_create') {
                    // Activate the quick create in the first column
                    self.widgets[0].add_quick_create();
                } else if (self.on_create && self.on_create !== 'quick_create') {
                    // Execute the given action
                    self.do_action(self.on_create, {
                        on_close: self.do_reload.bind(self),
                        additional_context: self.search_context,
                    });
                } else {
                    // Open the form view
                    self.add_record();
                }
            });
            this.update_buttons();
            this.$buttons.appendTo($node);
        }
    },
    update_buttons: function() {
        if (this.$buttons) {
            // In grouped mode, set 'Create' button as btn-default if there is no column
            var create_muted = !!this.grouped && this.widgets.length === 0 && this.is_action_enabled('group_create') && this.grouped_by_m2o;
            this.$buttons.find('.o-kanban-button-new')
                .toggleClass('btn-primary', !create_muted)
                .toggleClass('btn-default', create_muted);
        }
    },

    render_pager: function($node, options) {
        var self = this;
        this.pager = new Pager(this, this.dataset.size(), 1, this.limit, options);
        this.pager.appendTo($node);
        this.pager.on('pager_changed', this, function (state) {
            var limit_changed = (self.limit !== state.limit);

            self.limit = state.limit;
            self.load_records(state.current_min - 1)
                .then(function (data) {
                    self.data = data;

                    // Reset the scroll position to the top on page changed only
                    if (!limit_changed) {
                        self.scrollTop = 0;
                        self.trigger_up('scrollTo', {offset: 0});
                    }
                })
                .done(this.proxy('render'));
        });
        this.update_pager();
    },

    update_pager: function() {
        if (this.pager) {
            if (this.grouped) {
                this.pager.do_hide();
            } else {
                this.pager.update_state({size: this.dataset.size(), current_min: 1});
            }
        }
    },

    render: function () {
        // cleanup
        this.$el.css({display:'-webkit-flex'});
        this.$el.css({display:'flex'});
        this.$el.removeClass('o_kanban_ungrouped o_kanban_grouped o_kanban_nocontent');
        _.invoke(this.widgets, 'destroy');
        this.$el.empty();
        this.widgets = [];
        if (this.column_quick_create) {
            this.column_quick_create.destroy();
            this.column_quick_create = undefined;
        }

        this.record_options = {
            editable: this.is_action_enabled('edit'),
            deletable: this.is_action_enabled('delete'),
            fields: this.fields_view.fields,
            qweb: this.qweb,
            model: this.model,
            read_only_mode: this.options.read_only_mode,
        };

        // actual rendering
        var fragment = document.createDocumentFragment();
        if (this.data.grouped) {
            this.$el.addClass('o_kanban_grouped');
            this.render_grouped(fragment);
        } else {
            this.$el.addClass('o_kanban_ungrouped');
            this.render_ungrouped(fragment);
        }
        if (this.data.is_empty && this.widgets.length === 0 && (!this.data.grouped || !this.is_action_enabled('group_create') || !this.grouped_by_m2o)) {
            this.$el.css("display", "block");
            this.$el.addClass("o_kanban_nocontent");
            this.render_no_content(fragment);
        }

        this.$el.append(fragment);
    },

    render_no_content: function (fragment) {
        var content = qweb.render('KanbanView.nocontent', {content: this.no_content_msg});
        $(content).appendTo(fragment);
    },

    render_ungrouped: function (fragment) {
        var self = this;
        var options = _.clone(this.record_options);
        _.each(this.data.records, function (record) {
            var kanban_record = new KanbanRecord(self, record, options);
            self.widgets.push(kanban_record);
            kanban_record.appendTo(fragment);
        });

        // add empty invisible divs to make sure that all kanban records are left aligned
        for (var i = 0, ghost_div; i < 6; i++) {
            ghost_div = $("<div>").addClass("o_kanban_record o_kanban_ghost");
            ghost_div.appendTo(fragment);
        }
        this.postprocess_m2m_tags();
    },

    get_column_options: function () {
        return {
            editable: this.is_action_enabled('group_edit'),
            deletable: this.is_action_enabled('group_delete'),
            has_active_field: this.has_active_field(),
            grouped_by_m2o: this.grouped_by_m2o,
            relation: this.relation,
            qweb: this.qweb,
            fields: this.fields_view.fields,
            quick_create: this._is_quick_create_enabled(),
        };
    },

    render_grouped: function (fragment) {
        var self = this;

        // Drag'n'drop activation/deactivation
        var group_by_field_attrs = this.fields[this.group_by_field];

        // Deactivate the drag'n'drop if:
        // - field is a date or datetime since we group by month
        // - field is readonly
        var draggable = true;
        if (group_by_field_attrs) {
            if (group_by_field_attrs.type === "date" || group_by_field_attrs.type === "datetime") {
                var draggable = false;
            }
            else if (group_by_field_attrs.readonly !== undefined) {
                var draggable = !(group_by_field_attrs.readonly);
            }
        }
        var record_options = _.extend(this.record_options, {
            draggable: draggable,
        });

        var column_options = this.get_column_options();

        _.each(this.data.groups, function (group) {
            var column = new KanbanColumn(self, group, column_options, record_options);
            column.appendTo(fragment);
            self.widgets.push(column);
        });
        this.$el.sortable({
            axis: 'x',
            items: '> .o_kanban_group',
            handle: '.o_kanban_header',
            cursor: 'move',
            revert: 150,
            delay: 100,
            tolerance: 'pointer',
            forcePlaceholderSize: true,
            stop: function () {
                var ids = [];
                self.$('.o_kanban_group').each(function (index, u) {
                    ids.push($(u).data('id'));
                });
                self.resequence(ids);
            },
        });
        if (this.is_action_enabled('group_create') && this.grouped_by_m2o) {
            this.column_quick_create = new ColumnQuickCreate(this);
            this.column_quick_create.appendTo(fragment);
        }
        this.postprocess_m2m_tags();
    },

    add_record: function() {
        this.dataset.index = null;
        this.do_switch_view('form');
    },

    open_record: function (event, options) {
        if (this.dataset.select_id(event.data.id)) {
            this.do_switch_view('form', options);
        } else {
            this.do_warn("Kanban: could not find id#" + event.data.id);
        }
    },

    edit_record: function (event) {
        this.open_record(event, {mode: 'edit'});
    },

    delete_record: function (event) {
        var self = this;
        var record = event.data.record;
        function do_it() {
            return $.when(self.dataset.unlink([record.id])).done(function() {
                record.destroy();
                if (event.data.after) {
                    event.data.after();
                }
            });
        }
        if (this.options.confirm_on_delete) {
            Dialog.confirm(this, _t("Are you sure you want to delete this record ?"), { confirm_callback: do_it });
        } else {
            do_it();
        }
    },

    open_action: function (event) {
        var self = this;
        if (event.data.context) {
            event.data.context = new data.CompoundContext(event.data.context)
                .set_eval_context({
                    active_id: event.target.id,
                    active_ids: [event.target.id],
                    active_model: this.model,
                });
        }
        this.do_execute_action(event.data, this.dataset, event.target.id, _.bind(self.reload_record, this, event.target));
    },

    /*
    *  postprocessing of fields type many2many
    *  make the rpc request for all ids/model and insert value inside .o_form_field_many2manytags fields
    */
    postprocess_m2m_tags: function(records) {
        var self = this;
        if (!this.many2manys.length) {
            return;
        }
        var relations = {};
        records = records ? (records instanceof Array ? records : [records]) :
                  this.grouped ? Array.prototype.concat.apply([], _.pluck(this.widgets, 'records')) :
                  this.widgets;

        records.forEach(function(record) {
            self.many2manys.forEach(function(name) {
                var field = record.record[name];
                var $el = record.$('.oe_form_field.o_form_field_many2manytags[name=' + name + ']');
                // fields declared in the kanban view may not be used directly
                // in the template declaration, for example fields for which the
                // raw value is used -> $el[0] is undefined, leading to errors
                // in the following process. Preventing to add push the id here
                // prevents to make unnecessary calls to name_get
                if (! $el[0]) {
                    return;
                }
                if (!relations[field.relation]) {
                    relations[field.relation] = { ids: [], elements: {}, context: self.m2m_context[name]};
                }
                var rel = relations[field.relation];
                field.raw_value.forEach(function(id) {
                    rel.ids.push(id);
                    if (!rel.elements[id]) {
                        rel.elements[id] = [];
                    }
                    rel.elements[id].push($el[0]);
                });
            });
        });
       _.each(relations, function(rel, rel_name) {
            var dataset = new data.DataSetSearch(self, rel_name, self.dataset.get_context(rel.context));
            dataset.read_ids(_.uniq(rel.ids), ['name', 'color']).done(function(result) {
                result.forEach(function(record) {
                    // Does not display the tag if color = 10
                    if (typeof record.color !== 'undefined' && record.color != 10){
                        var $tag = $('<span>')
                            .addClass('o_tag o_tag_color_' + record.color)
                            .attr('title', _.str.escapeHTML(record.name));
                        $(rel.elements[record.id]).append($tag);
                    }
                });
                // we use boostrap tooltips for better and faster display
                self.$('span.o_tag').tooltip({delay: {'show': 50}});
            });
        });
    },
    resequence: function (ids) {
        if ((ids.length <= 1) || !this.relation) {
            return;
        }
        new data.DataSet(this, this.relation).resequence(ids).done(function (r) {
            if (!r) {
                console.warn('Resequence could not be complete. ' +
                    'Maybe the model does not have a "sequence" field?');
            }
        });
    },

    resequence_column: function (col) {
        if (_.indexOf(this.fields_keys, 'sequence') > -1) {
            this.dataset.resequence(col.get_ids());
        }
    },

    delete_column: function (event) {
        var self = this;
        var column = event.target;
        (new data.DataSet(this, this.relation)).unlink([column.id]).done(function() {
            if (column.is_empty()) {
                var index = self.widgets.indexOf(column);
                self.widgets.splice(index,1);
                column.destroy();
                self.update_buttons();
            } else {
                self.do_reload();
            }
        });
    },

    archive_records: function(event) {
        if (!this.has_active_field()) {
            return;
        }
        var active_value = !event.data.archive;
        var record_ids = [];
        _.each(event.target.records, function(kanban_record) {
            if (kanban_record.record.active.value != active_value) {
                record_ids.push(kanban_record.id);
            }
        });
        if (record_ids.length) {
            this.dataset.call('write', [record_ids, {active: active_value}])
                        .done(this.do_reload);
        }
    },

    reload_record: function (record) {
        var self = this;
        this.dataset.read_ids([record.id], this.fields_keys.concat(['__last_update'])).done(function(records) {
            if (records.length) {
                record.update(records[0]);
                self.postprocess_m2m_tags(record);
            } else {
                record.destroy();
            }
        });
    },

    add_record_to_column: function (event) {
        var self = this;
        var column = event.target;
        var record = event.data.record;
        var data = {};
        data[this.group_by_field] = event.target.id;
        this.dataset.write(record.id, data, {}).done(function () {
            if (!self.isDestroyed()) {
                self.reload_record(record);
                self.resequence_column(column);
            }
        }).fail(this.do_reload);
    },

    update_record: function(event) {
        var self = this;
        var record = event.target;
        return this.dataset.write(record.id, event.data)
            .done(function () {
                if (!self.isDestroyed()) {
                    self.reload_record(record);
                }
            });
    },

    column_add_record: function (event) {
        var self = this;
        var column = event.target;
        var context = {};
        context['default_' + this.group_by_field] = column.id;
        var name = event.data.value;
        this.dataset.name_create(name, context).done(function(data) {
            add_record(data[0]);
        }).fail(function(error, event) {
            event.preventDefault();
            var dialog = new form_common.FormViewDialog(self, {
                res_model: self.model,
                context: _.extend({"default_name": name}, context),
                title: _t("Create"),
                disable_multiple_selection: true,
                on_selected: function(element_ids) {
                    add_record(element_ids[0]);
                }
            }).open();
        });

        function add_record(id) {
            self.dataset.add_ids([id], -1);
            self.dataset.read_ids([id], self.fields_keys.concat(['__last_update'])).done(function(record) {
                column.add_record(record[0], {position: 'before'});
            });
        }
    },

    add_new_column: function (event) {
        var self = this;
        var model = new Model(this.relation, this.search_context);
        var name = event.data.value;
        model.call('name_create', [name], {
            context: this.search_context,
        }).then(function (result) {
            var dataset = new data.DataSetSearch(self, self.model, self.dataset.get_context(), []);
            var group_data = {
                records: [],
                title: event.data.value,
                id: result[0],
                attributes: {folded: false},
                dataset: dataset,
                values: {},
            };
            var options = self.get_column_options();
            var record_options = _.clone(self.record_options);
            var column = new KanbanColumn(self, group_data, options, record_options);
            column.insertBefore(self.$('.o_column_quick_create'));
            self.widgets.push(column);
            self.update_buttons();
            self.trigger_up('scrollTo', {selector: '.o_column_quick_create'});
        });
    },

    load_more: function (event) {
        var self = this;
        var column = event.target;
        var offset = column.offset + this.limit;
        return this.load_records(offset, column.dataset).then(function (result) {
            _.each(result.records, function (r) {
                column.add_record(r, {no_update: true});
                self.dataset.add_ids([r.id]);
            });
            column.offset += self.limit;
            column.remaining = Math.max(column.remaining - self.limit, 0);
            column.update_column();
            self.postprocess_m2m_tags(column.records.slice(column.offset));
        });
    },

    call_method: function (event) {
        var data = event.data;
        this.dataset.call(data.method, data.params).then(function() {
            if (data.callback) {
                data.callback();
            }
        });
    }
});

function qweb_add_if(node, condition) {
    if (node.attrs[qweb.prefix + '-if']) {
        condition = _.str.sprintf("(%s) and (%s)", node.attrs[qweb.prefix + '-if'], condition);
    }
    node.attrs[qweb.prefix + '-if'] = condition;
}

function transform_qweb_template (node, fvg, many2manys) {
    // Process modifiers
    if (node.tag && node.attrs.modifiers) {
        var modifiers = JSON.parse(node.attrs.modifiers || '{}');
        if (modifiers.invisible) {
            qweb_add_if(node, _.str.sprintf("!kanban_compute_domain(%s)", JSON.stringify(modifiers.invisible)));
        }
    }
    switch (node.tag) {
        case 'field':
            var ftype = fvg.fields[node.attrs.name].type;
            ftype = node.attrs.widget ? node.attrs.widget : ftype;
            if (ftype === 'many2many') {
                if (_.indexOf(many2manys, node.attrs.name) < 0) {
                    many2manys.push(node.attrs.name);
                }
                node.tag = 'div';
                node.attrs['class'] = (node.attrs['class'] || '') + ' oe_form_field o_form_field_many2manytags o_kanban_tags';
            } else if (fields_registry.contains(ftype)) {
                // do nothing, the kanban record will handle it
            } else {
                node.tag = qweb.prefix;
                node.attrs[qweb.prefix + '-esc'] = 'record.' + node.attrs.name + '.value';
            }
            break;
        case 'button':
        case 'a':
            var type = node.attrs.type || '';
            if (_.indexOf('action,object,edit,open,delete,url,set_cover'.split(','), type) !== -1) {
                _.each(node.attrs, function(v, k) {
                    if (_.indexOf('icon,type,name,args,string,context,states,kanban_states'.split(','), k) != -1) {
                        node.attrs['data-' + k] = v;
                        delete(node.attrs[k]);
                    }
                });
                if (node.attrs['data-string']) {
                    node.attrs.title = node.attrs['data-string'];
                }
                if (node.tag == 'a' && node.attrs['data-type'] != "url") {
                    node.attrs.href = '#';
                } else {
                    node.attrs.type = 'button';
                }

                var action_classes = " oe_kanban_action oe_kanban_action_" + node.tag;
                if (node.attrs['t-attf-class']) {
                    node.attrs['t-attf-class'] += action_classes;
                } else if (node.attrs['t-att-class']) {
                    node.attrs['t-att-class'] += " + '" + action_classes + "'";
                } else {
                    node.attrs['class'] = (node.attrs['class'] || '') + action_classes;
                }
            }
            break;
    }
    if (node.children) {
        for (var i = 0, ii = node.children.length; i < ii; i++) {
            transform_qweb_template(node.children[i], fvg, many2manys);
        }
    }
}

core.view_registry.add('kanban', KanbanView);

return KanbanView;

});
