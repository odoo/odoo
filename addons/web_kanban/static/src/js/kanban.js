openerp.web_kanban = function (openerp) {

var _t = openerp.web._t;
var QWeb = openerp.web.qweb;
QWeb.add_template('/web_kanban/static/src/xml/web_kanban.xml');
openerp.web.views.add('kanban', 'openerp.web_kanban.KanbanView');

openerp.web_kanban.KanbanView = openerp.web.View.extend({
    template: "KanbanView",
    init: function (parent, dataset, view_id, options) {
        this._super(parent);
        this.set_default_options(options);
        this.dataset = dataset;
        this.model = this.dataset.model;
        this.view_id = view_id;
        this.fields_view = {};
        this.fields_keys = [];
        this.group_by = null;
        this.records_states = {};
        this.groups_states = {};
        this.groups = [];
        this.nr_columns = 3;
        this.form_dialog = new openerp.web.FormDialog(this, {}, this.options.action_views_ids.form, dataset).start();
        this.form_dialog.on_form_dialog_saved.add_last(this.do_reload);
        this.aggregates = {};
        this.qweb = new QWeb2.Engine();
        this.qweb.debug = (window.location.search.indexOf('?debug') !== -1);
        this.qweb.default_dict = {
            '_' : _,
            '_t' : _t
        }
        this.has_been_loaded = $.Deferred();
        this.search_domain = this.search_context = this.search_group_by = null;
        this.currently_dragging = null;
    },
    start: function() {
        this._super();
        this.$element.find('button.oe_kanban_button_new').click(this.do_add_record);
        this.$groups = this.$element.find('.oe_kanban_groups tr');
        var context = new openerp.web.CompoundContext(this.dataset.get_context());
        return this.rpc('/web/view/load', {
                'model': this.model,
                'view_id': this.view_id,
                'view_type': 'kanban',
                context: context
            }, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data;
        this.fields_keys = _.keys(this.fields_view.fields);
        this.add_qweb_template();
        this.has_been_loaded.resolve();
    },
    add_qweb_template: function() {
        var group_operator = ['avg', 'max', 'min', 'sum', 'count']
        for (var i=0, ii=this.fields_view.arch.children.length; i < ii; i++) {
            var child = this.fields_view.arch.children[i];
            if (child.tag === "field") {
                for(j=0, jj=group_operator.length; j < jj;  j++) {
                    if (child.attrs[group_operator[j]]) {
                        this.aggregates[child.attrs.name] = child.attrs[group_operator[j]];
                        break;
                    }
                }
            }
            if (child.tag === "templates") {
                this.transform_qweb_template(child);
                this.qweb.add_template(openerp.web.json_node_to_xml(child));
                break;
            }
        }
    },
    transform_qweb_template: function(node) {
        var qweb_prefix = QWeb.prefix;
        switch (node.tag) {
            case 'field':
                node.tag = 't';
                node.attrs['t-esc'] = 'record.' + node.attrs['name'] + '.value';
                break
            case 'button':
            case 'a':
                var type = node.attrs.type || '';
                if (_.indexOf('action,object,edit,delete,color'.split(','), type) !== -1) {
                    _.each(node.attrs, function(v, k) {
                        if (_.indexOf('icon,type,name,string,context,states'.split(','), k) != -1) {
                            node.attrs['data-' + k] = v;
                            delete(node.attrs[k]);
                        }
                    });
                    if (node.attrs['data-states']) {
                        var states = _.map(node.attrs['data-states'].split(','), function(state) {
                            return "record.state.raw_value == '" + _.trim(state) + "'";
                        });
                        node.attrs['t-if'] = states.join(' or ');
                    }
                    if (node.attrs['data-string']) {
                        node.attrs.title = node.attrs['data-string'];
                    }
                    if (node.attrs['data-icon']) {
                        node.children = [{
                            tag: 'img',
                            attrs: {
                                src: '/web/static/src/img/icons/' + node.attrs['data-icon'] + '.png',
                                width: '16',
                                height: '16'
                            }
                        }];
                    }
                    if (node.tag == 'a') {
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
    do_search: function(domain, context, group_by) {
        var self = this;
        this.search_domain = domain;
        this.search_context = context;
        this.search_group_by = group_by;
        $.when(this.has_been_loaded).then(function() {
            self.group_by = group_by.length ? group_by[0] : self.fields_view.arch.attrs.default_group_by;
            self.datagroup = new openerp.web.DataGroup(self, self.model, domain, context, self.group_by ? [self.group_by] : []);
            self.datagroup.list(self.fields_keys, self.do_process_groups, self.do_process_dataset);
        });
    },
    do_process_groups: function(groups) {
        this.do_clear_groups();
        this.dataset.ids = [];
        var self = this,
            remaining = groups.length - 1,
            groups_array = [];
        _.each(groups, function (group, index) {
            var group_name = group_value = group.value,
                group_aggregates = {};
            if (group.value instanceof Array) {
                group_name = group.value[1];
                group_value = group.value[0];
            }
            _.each(self.aggregates, function(value, key) {
                group_aggregates[value] = group.aggregates[key];
            });
            var dataset = new openerp.web.DataSetSearch(self, self.dataset.model, group.context, group.domain);
            dataset.read_slice(self.fields_keys, {'domain': group.domain, 'context': group.context}, function(records) {
                self.dataset.ids.push.apply(self.dataset.ids, dataset.ids);
                groups_array[index] = new openerp.web_kanban.KanbanGroup(self, group_value, group_name, records, group_aggregates);
                if (!remaining--) {
                    self.dataset.index = self.dataset.ids.length ? 0 : null;
                    self.do_add_groups(groups_array);
                }
            });
        });
    },
    do_process_dataset: function(dataset) {
        var self = this;
        this.do_clear_groups();
        this.dataset.read_slice(this.fields_keys, {}, function(records) {
            var groups = [];
            while (records.length) {
                for (var i = 0; i < self.nr_columns; i++) {
                    if (!groups[i]) {
                        groups[i] = [];
                    }
                    groups[i].push(records.shift());
                }
            }
            for (var i = 0; i < groups.length; i++) {
                groups[i] = new openerp.web_kanban.KanbanGroup(self, false, false, _.compact(groups[i]));
            }
            self.do_add_groups(groups);
        });
    },
    do_reload: function() {
        this.do_search(this.search_domain, this.search_context, this.search_group_by);
    },
    do_clear_groups: function() {
        _.each(this.groups, function(group) {
            group.stop();
        });
        this.groups = [];
        //this.$element.find('.oe_kanban_groups_headers, .oe_kanban_groups_records').empty();
    },
    do_add_groups: function(groups) {
        var self = this;
        this.groups = groups;
        _.each(this.groups, function(group) {
            group.appendTo(self.$element.find('.oe_kanban_groups_headers'));
        });
        this.on_groups_started();
    },
    on_groups_started: function() {
        var self = this;
        this.compute_groups_width();
        if (this.group_by) {
            this.$element.find('.oe_kanban_column').sortable({
                connectWith: '.oe_kanban_column',
                handle : '.oe_kanban_draghandle',
                start: function(event, ui) {
                    self.currently_dragging = {
                        index : ui.item.index(),
                        group : ui.item.parents('.oe_kanban_column:first').data('widget')
                    }
                },
                stop: function(event, ui) {
                    var record = ui.item.data('widget'),
                        old_index = self.currently_dragging.index,
                        new_index = ui.item.index(),
                        old_group = self.currently_dragging.group,
                        new_group = ui.item.parents('.oe_kanban_column:first').data('widget');
                    if (!(old_group.title === new_group.title && old_group.value === new_group.value && old_index == new_index)) {
                        self.on_record_moved(record, old_group, old_index, new_group, new_index);
                    }
                },
                scroll: false
            });
        } else {
            this.$element.find('.oe_kanban_draghandle').removeClass('oe_kanban_draghandle');
        }
    },
    on_record_moved : function(record, old_group, old_index, new_group, new_index) {
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
            this.dataset.write(record.id, data, {}, record.do_reload);
            new_group.do_save_sequences();
        }
    },
    do_show: function () {
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    },
    compute_groups_width: function() {
        var unfolded = 0;
        _.each(this.groups, function(group) {
            unfolded += group.state.folded ? 0 : 1;
            group.$element.css('width', '');
        });
        _.each(this.groups, function(group) {
            if (!group.state.folded) {
                group.$element.css('width', Math.round(100/unfolded) + '%');
            }
        });
    }
});

openerp.web_kanban.KanbanGroup = openerp.web.Widget.extend({
    template: 'KanbanView.group_header',
    init: function (parent, value, title, records, aggregates) {
        var self = this;
        this._super(parent);
        this.view = parent;
        this.value = value;
        this.title = title;
        if (title === false) {
            this.title = _t('Undefined');
            this.undefined_title = true;
        }
        this.aggregates = aggregates || {};
        this.state = {};
        if (title || value) {
            var key = '' + this.view.group_by + '' + value;
            if (!this.view.groups_states[key]) {
                this.view.groups_states[key] = {
                    folded: false
                }
            }
            this.state = this.view.groups_states[key];
        }
        this.$records = null;
        this.records = _.map(records, function(record) {
            return new openerp.web_kanban.KanbanRecord(self, record);
        });
    },
    start: function() {
        var self = this,
            def = this._super();
        this.$records = $(QWeb.render('KanbanView.group_records_container', { widget : this}));
        this.$records.appendTo(this.view.$element.find('.oe_kanban_groups_records'));
        _.each(this.records, function(record) {
            record.appendTo(self.$records);
        });
        this.$element.find(".oe_kanban_fold_icon").click(function() {
            self.do_toggle_fold();
            self.view.compute_groups_width();
            return false;
        });
        if (this.state.folded) {
            this.do_toggle_fold();
        }
        this.$element.data('widget', this);
        this.$records.data('widget', this);
        return def;
    },
    stop: function() {
        this._super();
        this.$records.remove();
    },
    remove_record: function(id, remove_from_dataset) {
        for (var i = 0, ii = this.records.length; i < ii; i++) {
            if (this.records[i]['id'] === id) {
                this.records.splice(i, 1);
            }
        }
        if (remove_from_dataset) {
            var idx = _.indexOf(this.view.dataset.ids, id);
            if (idx > -1) {
                this.view.dataset.ids.splice(idx, 1);
            }
        }
    },
    do_toggle_fold: function(compute_width) {
        this.$element.toggleClass('oe_kanban_group_folded');
        this.$records.find('.oe_kanban_record').toggle();
        this.state.folded = this.$element.is('.oe_kanban_group_folded');
    },
    do_save_sequences: function() {
        var self = this;
        if (_.indexOf(this.view.fields_keys, 'sequence') > -1) {
            _.each(this.records, function(record, index) {
                self.view.dataset.write(record.id, { sequence : index });
            });
        }
    }
});

openerp.web_kanban.KanbanRecord = openerp.web.Widget.extend({
    template: 'KanbanView.record',
    init: function (parent, record) {
        this._super(parent);
        this.group = parent;
        this.view = parent.view;
        this.id = null;
        this.set_record(record);
        if (!this.view.records_states[this.id]) {
            this.view.records_states[this.id] = {
                folded: false
            };
        }
        this.state = this.view.records_states[this.id];
    },
    set_record: function(record) {
        this.id = record.id;
        this.record = this.transform_record(record);
    },
    start: function() {
        this._super();
        this.$element.data('widget', this);
        this.bind_events();
    },
    transform_record: function(record) {
        var self = this,
            new_record = {};
        _.each(record, function(value, name) {
            var r = _.clone(self.view.fields_view.fields[name]);
            r.raw_value = value;
            r.value = openerp.web.format_value(value, r);
            new_record[name] = r;
        });
        return new_record;
    },
    render: function() {
        var ctx = {
            record: this.record,
            widget: this
        }
        for (var p in this) {
            if (_.startsWith(p, 'kanban_')) {
                ctx[p] = _.bind(this[p], this);
            }
        }
        return this._super({
            'content': this.view.qweb.render('kanban-box', ctx)
        });
    },
    bind_events: function() {
        var self = this,
            $show_on_click = self.$element.find('.oe_kanban_box_show_onclick');
        $show_on_click.toggle(self.state.folded);
        this.$element.find('.oe_kanban_box_show_onclick_trigger').click(function() {
            $show_on_click.toggle();
            self.state.folded = !self.state.folded;
        });
        this.$element.find('.oe_kanban_action').click(function() {
            var $action = $(this),
                type = $action.data('type') || 'button',
                method = 'do_action_' + type;
            if (typeof self[method] === 'function') {
                self[method]($action);
            } else {
                self.do_warn("Kanban: no action for type : " + type);
            }
            return false;
        });
    },
    do_action_delete: function($action) {
        var self = this;
        if (confirm(_t("Qre you sure you want to delete this record ?"))) {
            return $.when(this.view.dataset.unlink([this.id])).then(function() {
                self.group.remove_record(self.id)
                self.stop();
            });
        }
    },
    do_action_edit: function($action) {
        var self = this;
        if ($action.attr('target') === 'dialog') {
            this.view.form_dialog.select_id(this.id).then(function() {
                self.view.form_dialog.open();
            });
        } else {
            if (self.view.dataset.select_id(this.id)) {
                this.view.do_switch_view('form');
            } else {
                this.do_warn("Kanban: could not find id#" + id);
            }
        }
    },
    do_action_color: function($action) {
        var self = this,
            colors = '#FFFFFF,#CCCCCC,#FFC7C7,#FFF1C7,#E3FFC7,#C7FFD5,#C7FFFF,#C7D5FF,#E3C7FF,#FFC7F1'.split(','),
            $cpicker = $(QWeb.render('KanbanColorPicker', { colors : colors, columns: 2 }));
        $action.after($cpicker);
        $cpicker.mouseenter(function() {
            clearTimeout($cpicker.data('timeoutId'));
        }).mouseleave(function(evt) {
            var timeoutId = setTimeout(function() { $cpicker.remove() }, 500);
            $cpicker.data('timeoutId', timeoutId);
        });
        $cpicker.find('a').click(function() {
            var data = {};
            data[$action.data('name')] = $(this).data('color');
            self.view.dataset.write(self.id, data, {}, function() {
                self.record[$action.data('name')] = $(this).data('color');
                self.do_reload();
            });
            $cpicker.remove();
            return false;
        });
    },
    do_action_object: function ($action) {
        var button_attrs = $action.data();
        this.view.do_execute_action(button_attrs, this.view.dataset, this.id, this.do_reload);
    },
    do_reload: function() {
        var self = this;
        this.view.dataset.read_ids([this.id], this.view.fields_keys, function(records) {
            if (records.length) {
                self.set_record(records[0]);
                self.do_render();
            } else {
                self.stop();
            }
        });
    },
    do_render: function() {
        this.$element.html(this.render());
        this.bind_events();
    },
    kanban_color: function(variable) {
        var number_of_color_schemes = 10,
            index = 0;
        switch (typeof(variable)) {
            case 'string':
                for (var i=0, ii=variable.length; i<ii; i++) {
                    index += variable.charCodeAt(i);
                }
                break;
            case 'number':
                index = Math.round(variable);
                break;
            default:
                return '';
        }
        var color = (index % number_of_color_schemes);
        return 'oe_kanban_color_' + color;
    },
    kanban_gravatar: function(email, size) {
        size = size || 22;
        var email_md5 = $.md5(email);
        return 'http://www.gravatar.com/avatar/' + email_md5 + '.png?s=' + size;
    },
    kanban_image: function(model, field, id) {
        id = id || '';
        return '/web/binary/image?session_id=' + this.session.session_id + '&model=' + model + '&field=' + field + '&id=' + id;
    },
    kanban_text_ellipsis: function(s, size) {
        size = size || 160;
        if (!s) {
            return '';
        }
        return s.substr(0, size) + '...';
    }
});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
