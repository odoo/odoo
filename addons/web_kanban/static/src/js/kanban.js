openerp.web_kanban = function (openerp) {

var QWeb = openerp.web.qweb;
QWeb.add_template('/web_kanban/static/src/xml/web_kanban.xml');
openerp.web.views.add('kanban', 'openerp.web_kanban.KanbanView');
openerp.web_kanban.KanbanView = openerp.web.View.extend({
    init: function (parent, dataset, view_id, options) {
        this._super(parent);
        this.set_default_options(options);
        this.dataset = dataset;
        this.model = dataset.model;
        this.domain = dataset.domain;
        this.context = dataset.context;
        this.view_id = view_id;
        this.fields_view = {};
        this.group_by = [];
        this.source_index = {};
        this.all_display_data = false;
        this.groups = [];
        this.qweb = new QWeb2.Engine();
        this.NO_OF_COLUMNS = 3;
        if (this.options.action_views_ids.form) {
            this.form_dialog = new openerp.web.FormDialog(this, {}, this.options.action_views_ids.form, dataset).start();
            this.form_dialog.on_form_dialog_saved.add_last(this.on_record_saved);
        }
    },
    start: function() {
        this._super();
        return this.rpc("/web/view/load", {"model": this.model, "view_id": this.view_id, "view_type": "kanban"}, this.on_loaded);
    },
    on_loaded: function(data) {
        var self = this;
        this.fields_view = data;
        this.add_qweb_template();
        if (this.qweb.has_template('kanban-box')) {
            this.do_actual_search();
        }
    },
    add_qweb_template: function() {
        for (var i=0, ii=this.fields_view.arch.children.length; i < ii; i++) {
            var child = this.fields_view.arch.children[i];
            if (child.tag === "templates") {
                this.transform_qweb_template(child);
                this.qweb.add_template(openerp.web.json_node_to_xml(child));
                break;
            }
        }
    },
    kanban_color: function(variable) {
        var number_of_color_schemes = 8,
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
        return 'oe_kanban_color_' + ((index % number_of_color_schemes) || number_of_color_schemes);
    },
    kanban_gravatar: function(email, size) {
        size = size || 22;
        var email_md5 = '2eb60ad22dadcf4dc456b28390a80268';
        return 'http://www.gravatar.com/avatar/' + email_md5 + '.png?s=' + size;
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
                            return "record.state.value == '" + _.trim(state) + "'";
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
    sort_group: function (first, second) {
        if (first.header && second.header)
        {
            first = first.header.toLowerCase();
            second = second.header.toLowerCase();
            if (first > second) return 1;
            else if (first < second) return -1;
            else return 0;
        }
        else return 0;
    },
    on_show_data: function() {
        var self = this;
        if (!this.group_by.length) {
            this.do_record_group();
        }
        self.all_display_data.sort(this.sort_group);
        this.$element.html(QWeb.render("KanbanView", {"data": self.all_display_data}));
        this.on_reload_kanban();
        var drag_handel = false;
        if (this.$element.find(".oe_kanban_draghandle").length > 0) {
            drag_handel = ".oe_kanban_draghandle";
        }
        if (!this.group_by.length) {
            drag_handel = true;
        }
        this.$element.find(".oe_column").sortable({
            connectWith: ".oe_column",
            handle : drag_handel,
            start: function(event, ui) {
                self.source_index['index'] = ui.item.index();
                self.source_index['column'] = ui.item.parent().attr('id');
            },
            stop: self.on_receive_record,
        });
        this.$element.find(".oe_column").disableSelection()
        this.$element.find('button.oe_kanban_button_new').click(this.do_add_record);
    },
    do_record_group: function() {
        if (this.NO_OF_COLUMNS) {
            var records = this.all_display_data[0].records;
            var record_per_group = Math.round((records).length / this.NO_OF_COLUMNS);
            this.all_display_data = [];
            for (var i=0, ii=this.NO_OF_COLUMNS; i < ii; i++) {
                this.all_display_data.push({'records': records.slice(0,record_per_group), 'value':false, 'header' : false, 'ids':[]});
                records.splice(0,record_per_group);
            }
        }
    },
    on_button_click: function (button_attrs, record_id) {
        var self = this;
        if (this.groups.length) {
            _.each(this.groups, function (group) {
                group.list([],
                    function (groups) {},
                    function (dataset) {
                        dataset.read_slice([], {}, function(records) {
                            var index = parseInt(_.indexOf(dataset.ids, record_id));
                            if(index >= 0) {
                                self.on_confirm_click(dataset, button_attrs, index, record_id);
                            }
                        });
                    }
                );
            });
        } else {
            var index = parseInt(_.indexOf(self.dataset.ids, record_id));
            if (index >= 0) {
                _.extend(self.dataset, {domain: self.domain, context: self.context});
                self.on_confirm_click(self.dataset, button_attrs, index, record_id);
            }
        }
    },
    on_confirm_click: function (dataset, button_attrs, index, record_id) {
        this.on_execute_button_click(dataset, button_attrs, record_id);
    },
    do_add_record: function() {
        this.dataset.index = null;
        this.do_switch_view('form');
    },
    do_edit_record: function(record_id) {
        if (this.form_dialog) {
            this.form_dialog.load_id(record_id);
            this.form_dialog.open();
        } else {
            this.notification.warn("Kanban", "No form view defined for this object");
        }
    },
    on_record_saved: function(r) {
        var id = this.form_dialog.form.datarecord.id;
        // TODO fme: reload record instead of all. need refactoring
        this.do_actual_search();
    },
    do_change_color: function(record_id, $e) {
        var self = this,
            id = record_id,
            colors = '#FFC7C7,#FFF1C7,#E3FFC7,#C7FFD5,#C7FFFF,#C7D5FF,#E3C7FF,#FFC7F1'.split(','),
            $cpicker = $(QWeb.render('KanbanColorPicker', { colors : colors, columns: 2 }));
        $e.after($cpicker);
        $cpicker.mouseenter(function() {
            clearTimeout($cpicker.data('timeoutId'));
        }).mouseleave(function(evt) {
            var timeoutId = setTimeout(function() { $cpicker.remove() }, 500);
            $cpicker.data('timeoutId', timeoutId);
        });
        $cpicker.find('a').click(function() {
            var data = {};
            data[$e.data('name')] = $(this).data('color');
            self.dataset.write(id, data, {}, function() {
                // TODO fme: reload record instead of all. need refactoring
                self.do_actual_search();
            });
            $cpicker.remove();
        });
    },
    do_delete: function (id) {
        var self = this;
        return $.when(this.dataset.unlink([id])).then(function () {
            self.drop_records(id);
        });
    },
    drop_records: function (id) {
        var self = this;
        _.each(self.all_display_data, function(data, index) {
            _.each(data.records, function(record, index_row) {
                if (parseInt(record.id) == id) {
                    self.all_display_data[index]['records'].splice(index_row, 1);
                    self.all_display_data[index]['ids'].splice(index_row, 1);
                    return false;
                }
            });
        });
        self.$element.find("#main_" + id).remove();
    },
    on_execute_button_click: function (dataset, button_attrs, record_id) {
        var self = this;
        this.do_execute_action(
            button_attrs, dataset,
            record_id, function () {
                var count = 1;
                _.each(self.all_display_data, function(data, index) {
                    self.dataset.read_ids( data.ids, [], function(records){
                        self.all_display_data[index].records = records;
                        if(self.all_display_data.length == count) {
                            self.do_actual_search();
                        }
                        count++;
                    });
                });
            }
        );
    },
    on_receive_record: function (event, ui) {
        var self = this;
        var from = ui.item.index();
        var search_action = false;
        var to = ui.item.prev().index() || 0;
        if (!ui.item.attr("id")) {
            return false;
        }
        // TODO fme: check what was this sequence
        if (self.fields_view.fields.sequence != undefined && ((self.source_index.index >= 0 && self.source_index.index != from) ||
                (self.source_index.column && self.source_index.column != ui.item.parent().attr('id')))) {
            var child_record = ui.item.parent().children();
            var data, sequence = 1, index = to;
            child_record.splice(0, to);
            var flag = false;
            if (to >= 0 && child_record) {
                var record_id = parseInt($(child_record).attr("id").split("_")[1]);
                if (record_id) {
                    _.each(self.all_display_data, function(data, index) {
                        _.each(data.records, function(record, index_row) {
                            if(record_id == record.id && record.sequence) {
                                sequence = record.sequence;
                                flag = true;
                                return false;
                            }
                        });
                        if(flag) {return false;}
                    });
                }
            }
            _.each(child_record, function (child) {
                var child_id = parseInt($(child).attr("id").split("_")[1]);
                if (child_id) {
                    flag = false;
                    _.each(self.all_display_data, function(data, index) {
                        _.each(data.records, function(record, index_row) {
                            if(parseInt(record.id) == child_id) {
                                self.all_display_data[index]['records'][index_row]['sequence'] = sequence;
                                flag = true;
                                return false;
                            }
                        });
                        if (flag) {return false;}
                    });
                    self.dataset.write(child_id, {sequence: sequence});
                    sequence++;
                    search_action = true;
                }
            });
        }
        if (self.group_by.length > 0 && self.source_index.column && self.source_index.column != ui.item.parent().attr('id')) {
            var value = ui.item.closest("td").attr("id");
            if (value) {
                var data_val = {};
                var wirte_id = parseInt(ui.item.attr("id").split("_")[1]);
                value = value.split("_")[1];
                if (value == 'false') {
                    value = false;
                }
                var update_record = false;
                _.each(self.all_display_data, function(data, index) {
                    _.each(data.records, function(record, index_row) {
                        if(parseInt(record.id) == wirte_id) {
                            self.all_display_data[index]['records'][index_row][self.group_by[0]] = value;
                            update_record = self.all_display_data[index]['records'].splice(index_row,1)
                            return false;
                        }
                    });
                    if (update_record) {return false;}
                });
                _.each(self.all_display_data, function(data, index) {
                    if (data.value == value || (data.value == 'false' && value == false)) {
                        self.all_display_data[index]['records'].push(update_record[0]);
                    }
                });
                data_val[self.group_by[0]] = value;
                self.dataset.write(wirte_id, data_val);
                search_action = true;
            }
        }
        if (search_action) {
            self.on_reload_kanban();
        }
        this.source_index = {};
    },
    on_reload_kanban: function (){
        var self = this;
        _.each(self.all_display_data, function(data, index) {
            if (data.records.length > 0){
                _.each(data.records, function(record) {
                    self.$element.find("#main_" + record.id).children().remove();
                    self.$element.find("#main_" + record.id).append(self.qweb.render('kanban-box', {
                        record: self.do_transform_record(record),
                        kanban_color: self.kanban_color,
                        kanban_gravatar: self.kanban_gravatar
                    }));
                });
            } else {
                self.$element.find("#column_" + data.value).remove();
                self.all_display_data.splice(index, 1);
            }
        });
        this.$element.find('.oe_kanban_action').click(this.on_action_clicked);
        this.$element.find('.oe_kanban_box_show_onclick_trigger').click(function() {
            $(this).parent('.oe_kanban_box').find('.oe_kanban_box_show_onclick').toggle();
        });
    },
    on_action_clicked: function(evt) {
        var $action = $(evt.currentTarget),
            record_id = parseInt($action.closest(".oe_kanban_record").attr("id").split('_')[1]),
            type = $action.data('type');
        if (type == 'delete') {
            this.do_delete(record_id);
        } else if (type == 'edit') {
            this.do_edit_record(record_id);
        } else if (type == 'color') {
            this.do_change_color(record_id, $action);
        } else {
            var button_attrs = $action.data();
            this.on_button_click(button_attrs, record_id);
        }
    },
    do_transform_record: function(record) {
        var self = this,
            new_record = {};
        _.each(record, function(value, name) {
            var r = _.clone(self.fields_view.fields[name]);
            r.raw_value = value;
            r.value = openerp.web.format_value(value, r);
            new_record[name] = r;
        });
        return new_record;
    },
    do_search: function (domains, contexts, group_by) {
        var self = this;
        this.rpc('/web/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: group_by
        }, function (results) {
            self.domain = results.domain;
            self.context = results.context;
            self.group_by = results.group_by;
            self.do_actual_search();
        });
    },
    do_actual_search : function () {
        var self = this,
            group_by = self.group_by;
        if (!group_by.length && this.fields_view.arch.attrs.default_group_by) {
            group_by = [this.fields_view.arch.attrs.default_group_by];
            self.group_by = group_by;
        }
        self.datagroup = new openerp.web.DataGroup(self, self.model, self.domain, self.context, group_by);
        self.dataset.context = self.context;
        self.dataset.domain = self.domain;
        self.datagroup.list([],
            function (groups) {
                self.groups = groups;
                self.do_render_group(groups);
            },
            function (dataset) {
                self.domain = dataset.domain;
                self.context = dataset.context;
                self.groups = [];
                self.dataset.read_slice([], {}, function(records) {
                    self.all_display_data = [{'records': records, 'value':false, 'header' : false, 'ids': self.dataset.ids}];
                    self.$element.find(".oe_kanban_view").remove();
                    self.on_show_data();
                });
            }
        );
    },
    do_render_group : function (datagroups) {
        this.all_display_data = [];
        var self = this;
        _.each(datagroups, function (group) {
            self.dataset.context = group.context;
            self.dataset.domain = group.domain;
            var group_name = group.value;
            var group_value = group.value;
            if (!group.value) {
                group_name = "Undefined";
                group_value = 'false';
            } else if (group.value instanceof Array) {
                group_name = group.value[1];
                group_value = group.value[0];
            }
            self.dataset.read_slice([], {}, function(records) {
                self.all_display_data.push({"value" : group_value, "records": records, 'header':group_name, 'ids': self.dataset.ids});
                if (datagroups.length == self.all_display_data.length) {
                    self.$element.find(".oe_kanban_view").remove();
                    self.on_show_data();
                }
            });
        });
    },
    do_show: function () {
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    }
});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
