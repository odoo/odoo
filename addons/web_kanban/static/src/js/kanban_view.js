odoo.define('web_kanban.KanbanView', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Model = require('web.Model');
var pyeval = require('web.pyeval');
var session = require('web.session');
var utils = require('web.utils');
var View = require('web.View');
var kanban_common = require('web_kanban.common');

var QWeb = core.qweb;
var _t = core._t;
var _lt = core._lt;
var fields_registry = kanban_common.registry;
var KanbanGroup = kanban_common.KanbanGroup;

var KanbanView = View.extend({
    template: "KanbanView",
    display_name: _lt('Kanban'),
    default_nr_columns: 1,
    view_type: "kanban",
    number_of_color_schemes: 10,
    init: function (parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, options);
        _.defaults(this.options, {
            "quick_creatable": true,
            "creatable": true,
            "create_text": undefined,
            "read_only_mode": false,
            "confirm_on_delete": true,
        });
        this.fields_view = {};
        this.fields_keys = [];
        this.group_by = null;
        this.group_by_field = {};
        this.grouped_by_m2o = false;
        this.many2manys = [];
        this.m2m_context = {};
        this.state = {
            groups : {},
            records : {}
        };
        this.groups = [];
        this.qweb = new QWeb2.Engine();
        this.qweb.debug = session.debug;
        this.qweb.default_dict = _.clone(QWeb.default_dict);
        this.has_been_loaded = $.Deferred();
        this.search_domain = this.search_context = this.search_group_by = null;
        this.currently_dragging = {};
        this.limit = options.limit || 40;
        this.add_group_mutex = new utils.Mutex();
    },
    view_loading: function(r) {
        return this.load_kanban(r);
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.$el.on('click', '.oe_kanban_dummy_cell', function() {
            if (self.$buttons) {
                self.$buttons.find('.oe_kanban_add_column').openerpBounce();
            }
        });
    },
    destroy: function() {
        this._super.apply(this, arguments);
        $('html').off('click.kanban');
    },
    get_quick_create_class: function () {
        return kanban_common.QuickCreate;
    },
    load_kanban: function(data) {
        this.fields_view = data;

        // use default order if defined in xml description
        var default_order = this.fields_view.arch.attrs.default_order,
            unsorted = !this.dataset._sort.length;
        if (unsorted && default_order) {
            this.dataset.set_sort(default_order.split(','));
        }
        this.$el.addClass(this.fields_view.arch.attrs['class']);
        this.$groups = this.$el.find('.oe_kanban_groups tr');
        this.fields_keys = _.keys(this.fields_view.fields);
        this.add_qweb_template();
        this.has_been_loaded.resolve();
        this.trigger('kanban_view_loaded', data);
        return $.when();
    },
    /**
     * Render the buttons according to the KanbanView.buttons template and
     * add listeners on it.
     * Set this.$buttons with the produced jQuery element
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should be inserted
     * $node may be undefined, in which case the ListView inserts them into this.options.$buttons
     * or into a div of its template
     */
    render_buttons: function($node) {
        var display = false;
        if (this.options.action_buttons !== false) {
            display = this.is_action_enabled('create');
        } else if (!this.view_id && !this.options.read_only_mode) {
            display = this.is_action_enabled('write') || this.is_action_enabled('create');
        }
        this.$buttons = $(QWeb.render("KanbanView.buttons", {'widget': this, display: display}));
        this.$buttons
            .on('click', 'button.oe_kanban_button_new', this.do_add_record)
            .on('click', '.oe_kanban_add_column', this.do_add_group);
        // Important: This should be done after do_search is finished so that
        // this.grouped_by_m2o is set
        this.$buttons.find('.oe_alternative').toggle(this.grouped_by_m2o);

        $node = $node || this.options.$buttons;
        if ($node) {
            this.$buttons.appendTo($node);
        } else {
            this.$('.oe_kanban_buttons').replaceWith(this.$buttons);
        }
    },
    _is_quick_create_enabled: function() {
        if (!this.options.quick_creatable || !this.is_action_enabled('create'))
            return false;
        if (this.fields_view.arch.attrs.quick_create !== undefined)
            return JSON.parse(this.fields_view.arch.attrs.quick_create);
        return !! this.group_by;
    },
    is_action_enabled: function(action) {
        if (action === 'create' && !this.options.creatable)
            return false;
        return this._super(action);
    },
    /*  add_qweb_template  */
    add_qweb_template: function() {
        for (var i=0, ii=this.fields_view.arch.children.length; i < ii; i++) {
            var child = this.fields_view.arch.children[i];
            if (child.tag === "templates") {
                this.transform_qweb_template(child);
                this.qweb.add_template(utils.json_node_to_xml(child));
                break;
            } else if (child.tag === 'field') {
                var ftype = child.attrs.widget || this.fields_view.fields[child.attrs.name].type;
                if(ftype == "many2many" && "context" in child.attrs) {
                    this.m2m_context[child.attrs.name] = child.attrs.context;
                }
            }
        }
    },
    transform_qweb_template: function(node) {
        var qweb_add_if = function(node, condition) {
            if (node.attrs[QWeb.prefix + '-if']) {
                condition = _.str.sprintf("(%s) and (%s)", node.attrs[QWeb.prefix + '-if'], condition);
            }
            node.attrs[QWeb.prefix + '-if'] = condition;
        };
        // Process modifiers
        if (node.tag && node.attrs.modifiers) {
            var modifiers = JSON.parse(node.attrs.modifiers || '{}');
            if (modifiers.invisible) {
                qweb_add_if(node, _.str.sprintf("!kanban_compute_domain(%s)", JSON.stringify(modifiers.invisible)));
            }
        }
        switch (node.tag) {
            case 'field':
                var ftype = this.fields_view.fields[node.attrs.name].type;
                ftype = node.attrs.widget ? node.attrs.widget : ftype;
                if (ftype === 'many2many') {
                    if (_.indexOf(this.many2manys, node.attrs.name) < 0) {
                        this.many2manys.push(node.attrs.name);
                    }
                    node.tag = 'div';
                    node.attrs['class'] = (node.attrs['class'] || '') + ' oe_form_field oe_tags';
                } else if (fields_registry.contains(ftype)) {
                    // do nothing, the kanban record will handle it
                } else {
                    node.tag = QWeb.prefix;
                    node.attrs[QWeb.prefix + '-esc'] = 'record.' + node.attrs['name'] + '.value';
                }
                break;
            case 'button':
            case 'a':
                var type = node.attrs.type || '';
                if (_.indexOf('action,object,edit,open,delete,url'.split(','), type) !== -1) {
                    _.each(node.attrs, function(v, k) {
                        if (_.indexOf('icon,type,name,args,string,context,states,kanban_states'.split(','), k) != -1) {
                            node.attrs['data-' + k] = v;
                            delete(node.attrs[k]);
                        }
                    });
                    if (node.attrs['data-string']) {
                        node.attrs.title = node.attrs['data-string'];
                    }
                    if (node.attrs['data-icon']) {
                        node.children = [{
                            tag: 'img',
                            attrs: {
                                src: session.prefix + '/web/static/src/img/icons/' + node.attrs['data-icon'] + '.png',
                                width: '16',
                                height: '16'
                            }
                        }];
                    }
                    if (node.tag == 'a' && node.attrs['data-type'] != "url") {
                        node.attrs.href = '#';
                    } else {
                        node.attrs.type = 'button';
                    }
                    node.attrs['class'] = (node.attrs['class'] || '') + ' oe_kanban_action oe_kanban_action_' + node.tag;
                }
                break;
        }
        if (node.children) {
            for (var i = 0, ii = node.children.length; i < ii; i++) {
                this.transform_qweb_template(node.children[i]);
            }
        }
    },
    do_add_record: function() {
        this.dataset.index = null;
        this.do_switch_view('form');
    },
    do_add_group: function() {
    },
    do_search: function(domain, context, group_by) {
        var self = this;
        this.search_domain = domain;
        this.search_context = context;
        this.search_group_by = group_by;
        return $.when(this.has_been_loaded).then(function() {
            self.group_by = group_by.length ? group_by[0] : self.fields_view.arch.attrs.default_group_by;
            self.group_by_field = self.fields_view.fields[self.group_by] || {};
            self.grouped_by_m2o = (self.group_by_field.type === 'many2one');
            self.$el.toggleClass('oe_kanban_grouped_by_m2o', self.grouped_by_m2o);
            var grouping_fields = self.group_by ? [self.group_by] : undefined;
            if (!_.isEmpty(grouping_fields)) {
                // ensure group_by fields are read.
                self.fields_keys = _.unique(self.fields_keys.concat(grouping_fields));
            }
            var grouping = new Model(self.dataset.model, context, domain).query(self.fields_keys).group_by(grouping_fields);
            return self.alive($.when(grouping)).then(function(groups) {
                self.remove_no_result();
                if (groups) {
                    return self.do_process_groups(groups);
                } else {
                    return self.do_process_dataset();
                }
            });
        });
    },
    do_process_groups: function(groups) {
        var self = this;

        // Check in the arch the fields to fetch on the stage to get tooltips data.
        // Fetching data is done in batch for all stages, to avoid doing multiple
        // calls. The first naive implementation of group_by_tooltip made a call
        // for each displayed stage and was quite limited.
        // Data for the group tooltip (group_by_tooltip) and to display stage-related
        // legends for kanban state management (states_legend) are fetched in
        // one call.
        var group_by_fields_to_read = [];
        var recurse = function(node) {
            if (node.tag === "field" && node.attrs && node.attrs.options) {
                var options = pyeval.py_eval(node.attrs.options);
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
            }
            _.each(node.children, function(child) {
                recurse(child);
            });
        };
        recurse(this.fields_view.arch);
        var group_ids = _.without(_.map(groups, function (elem) { return elem.attributes.value[0];}), undefined);
        if (this.grouped_by_m2o && group_ids.length && group_by_fields_to_read.length) {
            var group_data = new data.DataSet(
                this,
                this.group_by_field.relation).read_ids(group_ids, _.union(['display_name'], group_by_fields_to_read));
        }
        else { var group_data = $.Deferred().resolve({}); }

        this.$el.find('table:first').show();
        this.$el.removeClass('oe_kanban_ungrouped').addClass('oe_kanban_grouped');
        return $.when(group_data).then(function (results) {
            _.each(results, function (group_by_data) {
                var group = _.find(groups, function (elem) {return elem.attributes.value[0] == group_by_data.id;});
                if (group) {
                    group.values = group_by_data;
                }
            });
        }).done( function () {return self.add_group_mutex.exec(function() {
            self.do_clear_groups();
            self.dataset.ids = [];
            if (!groups.length) {
                self.no_result();
                return $.when();
            }
            self.nb_records = 0;
            var groups_array = [];
            return $.when.apply(null, _.map(groups, function (group, index) {
                var def = $.when([]);
                var dataset = new data.DataSetSearch(self, self.dataset.model,
                    new data.CompoundContext(self.dataset.get_context(), group.model.context()), group.model.domain());
                if (self.dataset._sort) {
                    dataset.set_sort(self.dataset._sort);
                }
                if (group.attributes.length >= 1) {
                    def = dataset.read_slice(self.fields_keys.concat(['__last_update']), { 'limit': self.limit });
                }
                return def.then(function(records) {
                        self.nb_records += records.length;
                        self.dataset.ids.push.apply(self.dataset.ids, dataset.ids);
                        groups_array[index] = new KanbanGroup(self, records, group, dataset);
                });
            })).then(function () {
                if(!self.nb_records) {
                    self.no_result();
                }
                if (self.dataset.index >= self.nb_records){
                    self.dataset.index = self.dataset.size() ? 0 : null;
                }
                return self.do_add_groups(groups_array).done(function() {
                    self.trigger('kanban_groups_processed');
                });
            });
        });});
    },
    do_process_dataset: function() {
        var self = this;
        this.$el.find('table:first').show();
        this.$el.removeClass('oe_kanban_grouped').addClass('oe_kanban_ungrouped');
        var def = $.Deferred();
        this.add_group_mutex.exec(function() {
            self.do_clear_groups();
            self.dataset.read_slice(self.fields_keys.concat(['__last_update']), { 'limit': self.limit }).done(function(records) {
                var kgroup = new KanbanGroup(self, records, null, self.dataset);
                if (!_.isEmpty(self.dataset.ids) && (self.dataset.index === null || self.dataset.index >= self.dataset.ids.length)) {
                    self.dataset.index = 0;
                } else if (_.isEmpty(self.dataset.ids)){
                    self.dataset.index = null;
                }
                self.do_add_groups([kgroup]).done(function() {
                    if (_.isEmpty(records)) {
                        self.no_result();
                    }
                    self.trigger('kanban_dataset_processed');
                    def.resolve();
                });
            }).done(null, function() {
                def.reject();
            });
            return def;
        });
        return def;
    },
    do_reload: function() {
        this.do_search(this.search_domain, this.search_context, this.search_group_by);
    },
    do_clear_groups: function() {
        var groups = this.groups.slice(0);
        this.groups = [];
        _.each(groups, function(group) {
            group.destroy();
        });
    },
    do_add_groups: function(groups) {
        var self = this;
        var $parent = this.$el.parent();
        this.$el.detach();
        _.each(groups, function(group) {
            self.groups[group.undefined_title ? 'unshift' : 'push'](group);
        });
        var $last_td = self.$el.find('.oe_kanban_groups_headers td:last');
        var groups_started = _.map(this.groups, function(group) {
            if (!group.is_started) {
                group.on("add_record", self, function () {
                    self.remove_no_result();
                });
                return group.insertBefore($last_td);
            }
        });
        return $.when.apply(null, groups_started).done(function () {
            self.on_groups_started();
            self.$el.appendTo($parent);
            _.each(self.groups, function(group) {
                group.compute_cards_auto_height();
            });
        });
    },
    on_groups_started: function() {
        var self = this;
        if (this.group_by || this.fields_keys.indexOf("sequence") !== -1) {
            // Kanban cards drag'n'drop
            var prev_widget, is_folded, record, $columns;
            if (this.group_by) {
                $columns = this.$el.find('.oe_kanban_column .oe_kanban_column_cards, .oe_kanban_column .oe_kanban_folded_column_cards');
            } else {
                $columns = this.$el.find('.oe_kanban_column_cards');
            }
            $columns.sortable({
                handle : '.oe_kanban_draghandle',
                start: function(event, ui) {
                    self.currently_dragging.index = ui.item.parent().children('.oe_kanban_record').index(ui.item);
                    self.currently_dragging.group = prev_widget = ui.item.parents('.oe_kanban_column:first').data('widget');
                    ui.item.find('*').on('click.prevent', function(ev) {
                        return false;
                    });
                    record = ui.item.data('widget');
                    record.$el.bind('mouseup',function(ev,ui){
                        if (is_folded) {
                            record.$el.hide();
                        }
                        record.$el.unbind('mouseup');
                    });
                    ui.placeholder.height(ui.item.height());
                },
                over: function(event, ui) {
                    var parent = $(event.target).parent();
                    prev_widget.highlight(false);
                    is_folded = parent.hasClass('oe_kanban_group_folded'); 
                    if (is_folded) {
                        var widget = parent.data('widget');
                        widget.highlight(true);
                        prev_widget = widget;
                    }
                 },
                revert: 150,
                stop: function(event, ui) {
                    prev_widget.highlight(false);
                    var old_index = self.currently_dragging.index;
                    var new_index = ui.item.parent().children('.oe_kanban_record').index(ui.item);
                    var old_group = self.currently_dragging.group;
                    var new_group = ui.item.parents('.oe_kanban_column:first').data('widget');
                    if (!(old_group.title === new_group.title && old_group.value === new_group.value && old_index == new_index)) {
                        self.on_record_moved(record, old_group, old_index, new_group, new_index);
                    }
                    setTimeout(function() {
                        // A bit hacky but could not find a better solution for Firefox (problem not present in chrome)
                        // http://stackoverflow.com/questions/274843/preventing-javascript-click-event-with-scriptaculous-drag-and-drop
                        ui.item.find('*').off('click.prevent');
                    }, 0);
                },
                scroll: false
            });
            // Keep connectWith out of the sortable initialization for performance sake:
            // http://www.planbox.com/blog/development/coding/jquery-ui-sortable-slow-to-bind.html
            $columns.sortable({ connectWith: $columns });

            // Kanban groups drag'n'drop
            var start_index;
            if (this.grouped_by_m2o) {
                this.$('.oe_kanban_groups_headers').sortable({
                    items: '.oe_kanban_group_header',
                    helper: 'clone',
                    axis: 'x',
                    opacity: 0.5,
                    scroll: false,
                    start: function(event, ui) {
                        start_index = ui.item.index();
                        self.$('.oe_kanban_record, .oe_kanban_quick_create').css({ visibility: 'hidden' });
                    },
                    stop: function(event, ui) {
                        var stop_index = ui.item.index();
                        if (start_index !== stop_index) {
                            var $start_column = self.$('.oe_kanban_groups_records .oe_kanban_column').eq(start_index);
                            var $stop_column = self.$('.oe_kanban_groups_records .oe_kanban_column').eq(stop_index);
                            var method = (start_index > stop_index) ? 'insertBefore' : 'insertAfter';
                            $start_column[method]($stop_column);
                            var tmp_group = self.groups.splice(start_index, 1)[0];
                            self.groups.splice(stop_index, 0, tmp_group);
                            var new_sequence = _.pluck(self.groups, 'value');
                            (new data.DataSet(self, self.group_by_field.relation)).resequence(new_sequence).done(function(r) {
                                if (r === false) {
                                    console.error("Kanban: could not resequence model '%s'. Probably no 'sequence' field.", self.group_by_field.relation);
                                }
                            });
                        }
                        self.$('.oe_kanban_record, .oe_kanban_quick_create').css({ visibility: 'visible' });
                    }
                });
            }
        } else {
            this.$el.find('.oe_kanban_draghandle').removeClass('oe_kanban_draghandle');
        }
        this.postprocess_m2m_tags();
    },
    on_record_moved : function(record, old_group, old_index, new_group, new_index) {
        var self = this;
        record.$el.find('[title]').tooltip('destroy');
        $(old_group.$el).add(new_group.$el).find('.oe_kanban_group_length').hide();
        if (old_group === new_group) {
            new_group.records.splice(old_index, 1);
            new_group.records.splice(new_index, 0, record);
            new_group.do_save_sequences();
        } else {
            old_group.records.splice(old_index, 1);
            new_group.records.splice(new_index, 0, record);
            record.group = new_group;
            var data = {};
            data[this.group_by] = new_group.value;
            this.dataset.write(record.id, data, {}).done(function() {
                record.do_reload();
                new_group.do_save_sequences();
                if (new_group.state.folded) {
                    new_group.do_action_toggle_fold();
                    record.prependTo(new_group.$records.find('.oe_kanban_column_cards'));
                }
            }).fail(function(error, evt) {
                evt.preventDefault();
                alert(_t("An error has occured while moving the record to this group: ") + error.data.message);
                self.do_reload(); // TODO: use draggable + sortable in order to cancel the dragging when the rcp fails
            });
        }
    },

    do_show: function() {
        this.do_push_state({});
        return this._super();
    },
    open_record: function(id, editable) {
        if (this.dataset.select_id(id)) {
            this.do_switch_view('form', null, { mode: editable ? "edit" : undefined });
        } else {
            this.do_warn("Kanban: could not find id#" + id);
        }
    },
    no_result: function() {
        var self = this;
        if (this.groups.group_by
            || !this.options.action
            || (!this.options.action.help && !this.options.action.get_empty_list_help)) {
            return;
        }
        this.$el.css("position", "relative");
        $(QWeb.render('KanbanView.nocontent', { content : this.options.action.get_empty_list_help || this.options.action.help})).insertBefore(this.$('table:first'));
        this.$el.find('.oe_view_nocontent').click(function() {
            self.$buttons.openerpBounce();
        });
    },
    remove_no_result: function() {
        this.$el.css("position", "");
        this.$el.find('.oe_view_nocontent').remove();
    },

    /*
    *  postprocessing of fields type many2many
    *  make the rpc request for all ids/model and insert value inside .oe_tags fields
    */
    postprocess_m2m_tags: function() {
        var self = this;
        if (!this.many2manys.length) {
            return;
        }
        var relations = {};
        this.groups.forEach(function(group) {
            group.records.forEach(function(record) {
                self.many2manys.forEach(function(name) {
                    var field = record.record[name];
                    var $el = record.$('.oe_form_field.oe_tags[name=' + name + ']').empty();
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
        });
       _.each(relations, function(rel, rel_name) {
            var dataset = new data.DataSetSearch(self, rel_name, self.dataset.get_context(rel.context));
            dataset.name_get(_.uniq(rel.ids)).done(function(result) {
                result.forEach(function(nameget) {
                    $(rel.elements[nameget[0]]).append('<span class="oe_tag">' + _.str.escapeHTML(nameget[1]) + '</span>');
                });
            });
        });
    }
});

core.view_registry.add('kanban', KanbanView);

return KanbanView;

});


odoo.define(function (require) {

var core = require('web.core');
var data = require('web.data');
var web_client = require('web.web_client');
var kanban_common = require('web_kanban.common');
var KanbanView = require('web_kanban.KanbanView');

var KanbanGroup = kanban_common.KanbanGroup;
var _t = core._t;

KanbanView.include({
    do_add_group: function() {
        var self = this;
        self.do_action({
            name: _t("Add column"),
            res_model: self.group_by_field.relation,
            views: [[false, 'form']],
            type: 'ir.actions.act_window',
            target: "new",
            context: self.dataset.get_context(),
            flags: {
                action_buttons: true,
            }
        });
        var am = web_client.action_manager;
        var form = am.dialog_widget.views.form.controller;
        form.on("on_button_cancel", am.dialog, am.dialog.close);
        form.on('record_created', self, function(r) {
            (new data.DataSet(self, self.group_by_field.relation)).name_get([r]).done(function(new_record) {
                am.dialog.close();
                var domain = self.dataset.domain.slice(0);
                domain.push([self.group_by, '=', new_record[0][0]]);
                var dataset = new data.DataSetSearch(self, self.dataset.model, self.dataset.get_context(), domain);
                var datagroup = {
                    get: function(key) {
                        return this[key];
                    },
                    value: new_record[0],
                    length: 0,
                };
                var new_group = new KanbanGroup(self, [], datagroup, dataset);
                self.do_add_groups([new_group]).done(function() {
                    $(window).scrollTo(self.groups.slice(-1)[0].$el, { axis: 'x' });
                });
            });
        });
    },
});

});
