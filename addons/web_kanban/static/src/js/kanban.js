openerp.web_kanban = function (instance) {

var _t = instance.web._t,
   _lt = instance.web._lt;
var QWeb = instance.web.qweb;
instance.web.views.add('kanban', 'instance.web_kanban.KanbanView');

instance.web_kanban.KanbanView = instance.web.View.extend({
    template: "KanbanView",
    display_name: _lt('Kanban'),
    default_nr_columns: 1,
    view_type: "kanban",
    quick_create_class: "instance.web_kanban.QuickCreate",
    number_of_color_schemes: 10,
    init: function (parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, options);
        var self = this;
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
        this.state = {
            groups : {},
            records : {}
        };
        this.groups = [];
        this.aggregates = {};
        this.group_operators = ['avg', 'max', 'min', 'sum', 'count'];
        this.qweb = new QWeb2.Engine();
        this.qweb.debug = instance.session.debug;
        this.qweb.default_dict = _.clone(QWeb.default_dict);
        this.has_been_loaded = $.Deferred();
        this.search_domain = this.search_context = this.search_group_by = null;
        this.currently_dragging = {};
        this.limit = options.limit || 40;
        this.add_group_mutex = new $.Mutex();
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
    load_kanban: function(data) {
        this.fields_view = data;
        this.$el.addClass(this.fields_view.arch.attrs['class']);
        this.$buttons = $(QWeb.render("KanbanView.buttons", {'widget': this}));
        if (this.options.$buttons) {
            this.$buttons.appendTo(this.options.$buttons);
        } else {
            this.$el.find('.oe_kanban_buttons').replaceWith(this.$buttons);
        }
        this.$buttons
            .on('click', 'button.oe_kanban_button_new', this.do_add_record)
            .on('click', '.oe_kanban_add_column', this.do_add_group);
        this.$groups = this.$el.find('.oe_kanban_groups tr');
        this.fields_keys = _.keys(this.fields_view.fields);
        this.add_qweb_template();
        this.has_been_loaded.resolve();
        this.trigger('kanban_view_loaded', data);
        return $.when();
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
    /*  add_qweb_template
    *   select the nodes into the xml and send to extract_aggregates the nodes with TagName="field"
    */
    add_qweb_template: function() {
        for (var i=0, ii=this.fields_view.arch.children.length; i < ii; i++) {
            var child = this.fields_view.arch.children[i];
            if (child.tag === "templates") {
                this.transform_qweb_template(child);
                this.qweb.add_template(instance.web.json_node_to_xml(child));
                break;
            } else if (child.tag === 'field') {
                this.extract_aggregates(child);
            }
        }
    },
    /*  extract_aggregates
    *   extract the agggregates from the nodes (TagName="field")
    */
    extract_aggregates: function(node) {
        for (var j = 0, jj = this.group_operators.length; j < jj;  j++) {
            if (node.attrs[this.group_operators[j]]) {
                this.aggregates[node.attrs.name] = node.attrs[this.group_operators[j]];
                break;
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
                } else if (instance.web_kanban.fields_registry.contains(ftype)) {
                    // do nothing, the kanban record will handle it
                } else {
                    node.tag = QWeb.prefix;
                    node.attrs[QWeb.prefix + '-esc'] = 'record.' + node.attrs['name'] + '.value';
                }
                break;
            case 'button':
            case 'a':
                var type = node.attrs.type || '';
                if (_.indexOf('action,object,edit,open,delete'.split(','), type) !== -1) {
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
                                src: instance.session.prefix + '/web/static/src/img/icons/' + node.attrs['data-icon'] + '.png',
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
        var am = instance.webclient.action_manager;
        var form = am.dialog_widget.views.form.controller;
        form.on("on_button_cancel", am.dialog, am.dialog.close);
        form.on('record_created', self, function(r) {
            (new instance.web.DataSet(self, self.group_by_field.relation)).name_get([r]).done(function(new_record) {
                am.dialog.close();
                var domain = self.dataset.domain.slice(0);
                domain.push([self.group_by, '=', new_record[0][0]]);
                var dataset = new instance.web.DataSetSearch(self, self.dataset.model, self.dataset.get_context(), domain);
                var datagroup = {
                    get: function(key) {
                        return this[key];
                    },
                    value: new_record[0],
                    length: 0,
                    aggregates: {},
                };
                var new_group = new instance.web_kanban.KanbanGroup(self, [], datagroup, dataset);
                self.do_add_groups([new_group]).done(function() {
                    $(window).scrollTo(self.groups.slice(-1)[0].$el, { axis: 'x' });
                });
            });
        });
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
            self.$buttons.find('.oe_alternative').toggle(self.grouped_by_m2o);
            self.$el.toggleClass('oe_kanban_grouped_by_m2o', self.grouped_by_m2o);
            var grouping_fields = self.group_by ? [self.group_by].concat(_.keys(self.aggregates)) : undefined;
            if (!_.isEmpty(grouping_fields)) {
                // ensure group_by fields are read.
                self.fields_keys = _.unique(self.fields_keys.concat(grouping_fields));
            }
            var grouping = new instance.web.Model(self.dataset.model, context, domain).query(self.fields_keys).group_by(grouping_fields);
            return self.alive($.when(grouping)).done(function(groups) {
                self.remove_no_result();
                if (groups) {
                    self.do_process_groups(groups);
                } else {
                    self.do_process_dataset();
                }
            });
        });
    },
    do_process_groups: function(groups) {
        var self = this;
        this.$el.find('table:first').show();
        this.$el.removeClass('oe_kanban_ungrouped').addClass('oe_kanban_grouped');
        this.add_group_mutex.exec(function() {
            self.do_clear_groups();
            self.dataset.ids = [];
            if (!groups.length) {
                self.no_result();
                return false;
            }
            self.nb_records = 0;
            var remaining = groups.length - 1,
                groups_array = [];
            return $.when.apply(null, _.map(groups, function (group, index) {
                var def = $.when([]);
                var dataset = new instance.web.DataSetSearch(self, self.dataset.model,
                    new instance.web.CompoundContext(self.dataset.get_context(), group.model.context()), group.model.domain());
                if (group.attributes.length >= 1) {
                    def = dataset.read_slice(self.fields_keys.concat(['__last_update']), { 'limit': self.limit });
                }
                return def.then(function(records) {
                        self.nb_records += records.length;
                        self.dataset.ids.push.apply(self.dataset.ids, dataset.ids);
                        groups_array[index] = new instance.web_kanban.KanbanGroup(self, records, group, dataset);
                        if (!remaining--) {
                            self.dataset.index = self.dataset.size() ? 0 : null;
                            return self.do_add_groups(groups_array);
                        }
                });
            })).then(function () {
                if(!self.nb_records) {
                    self.no_result();
                }
            });
        });
    },
    do_process_dataset: function() {
        var self = this;
        this.$el.find('table:first').show();
        this.$el.removeClass('oe_kanban_grouped').addClass('oe_kanban_ungrouped');
        this.add_group_mutex.exec(function() {
            var def = $.Deferred();
            self.do_clear_groups();
            self.dataset.read_slice(self.fields_keys.concat(['__last_update']), { 'limit': self.limit }).done(function(records) {
                var kgroup = new instance.web_kanban.KanbanGroup(self, records, null, self.dataset);
                self.do_add_groups([kgroup]).done(function() {
                    if (_.isEmpty(records)) {
                        self.no_result();
                    }
                    def.resolve();
                });
            }).done(null, function() {
                def.reject();
            });
            return def;
        });
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
                    })
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
                            var $start_column = $('.oe_kanban_groups_records .oe_kanban_column').eq(start_index);
                            var $stop_column = $('.oe_kanban_groups_records .oe_kanban_column').eq(stop_index);
                            var method = (start_index > stop_index) ? 'insertBefore' : 'insertAfter';
                            $start_column[method]($stop_column);
                            var tmp_group = self.groups.splice(start_index, 1)[0];
                            self.groups.splice(stop_index, 0, tmp_group);
                            var new_sequence = _.pluck(self.groups, 'value');
                            (new instance.web.DataSet(self, self.group_by_field.relation)).resequence(new_sequence).done(function(r) {
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
        $(old_group.$el).add(new_group.$el).find('.oe_kanban_aggregates, .oe_kanban_group_length').hide();
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
        if (this.$buttons) {
            this.$buttons.show();
        }
        this.do_push_state({});
        return this._super();
    },
    do_hide: function () {
        if (this.$buttons) {
            this.$buttons.hide();
        }
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
                    if (!relations[field.relation]) {
                        relations[field.relation] = { ids: [], elements: {}};
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
            var dataset = new instance.web.DataSetSearch(self, rel_name, self.dataset.get_context());
            dataset.name_get(_.uniq(rel.ids)).done(function(result) {
                result.forEach(function(nameget) {
                    $(rel.elements[nameget[0]]).append('<span class="oe_tag">' + _.str.escapeHTML(nameget[1]) + '</span>');
                });
            });
        });
    }
});


function get_class(name) {
    return new instance.web.Registry({'tmp' : name}).get_object("tmp");
}

instance.web_kanban.KanbanGroup = instance.web.Widget.extend({
    template: 'KanbanView.group_header',
    init: function (parent, records, group, dataset) {
        var self = this;
        this._super(parent);
        this.$has_been_started = $.Deferred();
        this.view = parent;
        this.group = group;
        this.dataset = dataset;
        this.dataset_offset = 0;
        this.aggregates = {};
        this.value = this.title = null;
        if (this.group) {
            this.value = group.get('value');
            this.title = group.get('value');
            if (this.value instanceof Array) {
                this.title = this.value[1];
                this.value = this.value[0];
            }
            var field = this.view.group_by_field;
            if (!_.isEmpty(field)) {
                try {
                    this.title = instance.web.format_value(group.get('value'), field, false);
                } catch(e) {}
            }
            _.each(this.view.aggregates, function(value, key) {
                self.aggregates[value] = instance.web.format_value(group.get('aggregates')[key], {type: 'float'});
            });
        }

        if (this.title === false) {
            this.title = _t('Undefined');
            this.undefined_title = true;
        }
        var key = this.view.group_by + '-' + this.value;
        if (!this.view.state.groups[key]) {
            this.view.state.groups[key] = {
                folded: group ? group.get('folded') : false
            };
        }
        this.state = this.view.state.groups[key];
        this.$records = null;

        this.records = [];
        this.$has_been_started.done(function() {
            self.do_add_records(records);
        });
    },
    start: function() {
        var self = this;
        if (! self.view.group_by) {
            self.$el.addClass("oe_kanban_no_group");
            self.quick = new (get_class(self.view.quick_create_class))(this, self.dataset, {}, false)
                .on('added', self, self.proxy('quick_created'));
            self.quick.replace($(".oe_kanban_no_group_qc_placeholder"));
        }
        this.$records = $(QWeb.render('KanbanView.group_records_container', { widget : this}));
        this.$records.insertBefore(this.view.$el.find('.oe_kanban_groups_records td:last'));

        this.$el.on('click', '.oe_kanban_group_dropdown li a', function(ev) {
            var fn = 'do_action_' + $(ev.target).data().action;
            if (typeof(self[fn]) === 'function') {
                self[fn]($(ev.target));
            }
        });

        this.$el.find('.oe_kanban_add').click(function () {
            if (self.view.quick) {
                self.view.quick.trigger('close');
            }
            if (self.quick) {
                return false;
            }
            self.view.$el.find('.oe_view_nocontent').hide();
            var ctx = {};
            ctx['default_' + self.view.group_by] = self.value;
            self.quick = new (get_class(self.view.quick_create_class))(this, self.dataset, ctx, true)
                .on('added', self, self.proxy('quick_created'))
                .on('close', self, function() {
                    self.view.$el.find('.oe_view_nocontent').show();
                    this.quick.destroy();
                    delete self.view.quick;
                    delete this.quick;
                });
            self.quick.appendTo($(".oe_kanban_group_list_header", self.$records));
            self.quick.focus();
            self.view.quick = self.quick;
        });
        // Add bounce effect on image '+' of kanban header when click on empty space of kanban grouped column.
        this.$records.on('click', '.oe_kanban_show_more', this.do_show_more);
        if (this.state.folded) {
            this.do_toggle_fold();
        }
        this.$el.data('widget', this);
        this.$records.data('widget', this);
        this.$has_been_started.resolve();
        var add_btn = this.$el.find('.oe_kanban_add');
        add_btn.tooltip({delay: { show: 500, hide:1000 }});
        this.$records.find(".oe_kanban_column_cards").click(function (ev) {
            if (ev.target == ev.currentTarget) {
                if (!self.state.folded) {
                    add_btn.openerpBounce();
                }
            }
        });
        this.is_started = true;
        var def_tooltip = this.fetch_tooltip();
        return $.when(def_tooltip);
    },
    fetch_tooltip: function() {
        if (! this.group)
            return;
        var field_name = this.view.group_by;
        var field = this.view.group_by_field;
        var field_desc = null;
        var recurse = function(node) {
            if (node.tag === "field" && node.attrs.name === field_name) {
                field_desc = node;
                return;
            }
            _.each(node.children, function(child) {
                if (field_desc === null)
                    recurse(child);
            });
        };
        recurse(this.view.fields_view.arch);
        if (! field_desc)
            return;
        var options = instance.web.py_eval(field_desc.attrs.options || '{}')
        if (! options.tooltip_on_group_by)
            return;

        var self = this;
        if (this.value) {
            return (new instance.web.Model(field.relation)).query([options.tooltip_on_group_by])
                    .filter([["id", "=", this.value]]).first().then(function(res) {
                self.tooltip = res[options.tooltip_on_group_by];
                self.$(".oe_kanban_group_title_text").attr("title", self.tooltip || self.title || "").tooltip();
            });
        }
    },
    compute_cards_auto_height: function() {
        // oe_kanban_no_auto_height is an empty class used to disable this feature
        if (!this.view.group_by) {
            var min_height = 0;
            var els = [];
            _.each(this.records, function(r) {
                var $e = r.$el.children(':first:not(.oe_kanban_no_auto_height)').css('min-height', 0);
                if ($e.length) {
                    els.push($e[0]);
                    min_height = Math.max(min_height, $e.outerHeight());
                }
            });
            $(els).css('min-height', min_height);
        }
    },
    destroy: function() {
        this._super();
        if (this.$records) {
            this.$records.remove();
        }
    },
    do_show_more: function(evt) {
        var self = this;
        var ids = self.view.dataset.ids.splice(0);
        return this.dataset.read_slice(this.view.fields_keys.concat(['__last_update']), {
            'limit': self.view.limit,
            'offset': self.dataset_offset += self.view.limit
        }).then(function(records) {
            self.view.dataset.ids = ids.concat(self.dataset.ids);
            self.do_add_records(records);
            self.compute_cards_auto_height();
            self.view.postprocess_m2m_tags();
            return records;
        });
    },
    do_add_records: function(records, prepend) {
        var self = this;
        var $list_header = this.$records.find('.oe_kanban_group_list_header');
        var $show_more = this.$records.find('.oe_kanban_show_more');
        var $cards = this.$records.find('.oe_kanban_column_cards');

        _.each(records, function(record) {
            var rec = new instance.web_kanban.KanbanRecord(self, record);
            if (!prepend) {
                rec.appendTo($cards);
                self.records.push(rec);
            } else {
                rec.prependTo($cards);
                self.records.unshift(rec);
            }
        });
        if ($show_more.length) {
            var size = this.dataset.size();
            $show_more.toggle(this.records.length < size).find('.oe_kanban_remaining').text(size - this.records.length);
        }
    },
    remove_record: function(id, remove_from_dataset) {
        for (var i = 0; i < this.records.length; i++) {
            if (this.records[i]['id'] === id) {
                this.records.splice(i, 1);
                i--;
            }
        }
    },
    do_toggle_fold: function(compute_width) {
        this.$el.add(this.$records).toggleClass('oe_kanban_group_folded');
        this.state.folded = this.$el.is('.oe_kanban_group_folded');
        this.$("ul.oe_kanban_group_dropdown li a[data-action=toggle_fold]").text((this.state.folded) ? _t("Unfold") : _t("Fold"));
    },
    do_action_toggle_fold: function() {
        this.do_toggle_fold();
    },
    do_action_edit: function() {
        var self = this;
        self.do_action({
            res_id: this.value,
            name: _t("Edit column"),
            res_model: self.view.group_by_field.relation,
            views: [[false, 'form']],
            type: 'ir.actions.act_window',
            target: "new",
            flags: {
                action_buttons: true,
            }
        });
        var am = instance.webclient.action_manager;
        var form = am.dialog_widget.views.form.controller;
        form.on("on_button_cancel", am.dialog, function() { return am.dialog.$dialog_box.modal('hide'); });
        form.on('record_saved', self, function() {
            am.dialog.$dialog_box.modal('hide');
            self.view.do_reload();
        });
    },
    do_action_delete: function() {
        var self = this;
        if (confirm(_t("Are you sure to remove this column ?"))) {
            (new instance.web.DataSet(self, self.view.group_by_field.relation)).unlink([self.value]).done(function(r) {
                self.view.do_reload();
            });
        }
    },
    do_save_sequences: function() {
        var self = this;
        if (_.indexOf(this.view.fields_keys, 'sequence') > -1) {
            var new_sequence = _.pluck(this.records, 'id');
            self.view.dataset.resequence(new_sequence);
        }
    },
    /**
     * Handles a newly created record
     *
     * @param {id} id of the newly created record
     */
    quick_created: function (record) {
        var id = record, self = this;
        self.view.remove_no_result();
        self.trigger("add_record");
        this.dataset.read_ids([id], this.view.fields_keys)
            .done(function (records) {
                self.view.dataset.ids.push(id);
                self.do_add_records(records, true);
            });
    },
    highlight: function(show){
        if(show){
            this.$el.addClass('oe_kanban_column_higlight');
            this.$records.addClass('oe_kanban_column_higlight');
        }else{
            this.$el.removeClass('oe_kanban_column_higlight');
            this.$records.removeClass('oe_kanban_column_higlight');
        }
    }
});

instance.web_kanban.KanbanRecord = instance.web.Widget.extend({
    template: 'KanbanView.record',
    init: function (parent, record) {
        this._super(parent);
        this.group = parent;
        this.view = parent.view;
        this.id = null;
        this.set_record(record);
        if (!this.view.state.records[this.id]) {
            this.view.state.records[this.id] = {
                folded: false
            };
        }
        this.state = this.view.state.records[this.id];
        this.fields = {};
    },
    set_record: function(record) {
        var self = this;
        this.id = record.id;
        this.values = {};
        _.each(record, function(v, k) {
            self.values[k] = {
                value: v
            };
        });
        this.record = this.transform_record(record);
    },
    start: function() {
        var self = this;
        this._super();
        this.init_content();
    },
    init_content: function() {
        var self = this;
        self.sub_widgets = [];
        this.$("[data-field_id]").each(function() {
            self.add_widget($(this));
        });
        this.$el.data('widget', this);
        this.bind_events();
    },
    transform_record: function(record) {
        var self = this,
            new_record = {};
        _.each(record, function(value, name) {
            var r = _.clone(self.view.fields_view.fields[name] || {});
            if ((r.type === 'date' || r.type === 'datetime') && value) {
                r.raw_value = instance.web.auto_str_to_date(value);
            } else {
                r.raw_value = value;
            }
            r.value = instance.web.format_value(value, r);
            new_record[name] = r;
        });
        return new_record;
    },
    renderElement: function() {
        this.qweb_context = {
            instance: instance,
            record: this.record,
            widget: this,
            read_only_mode: this.view.options.read_only_mode,
        };
        for (var p in this) {
            if (_.str.startsWith(p, 'kanban_')) {
                this.qweb_context[p] = _.bind(this[p], this);
            }
        }
        var $el = instance.web.qweb.render(this.template, {
            'widget': this,
            'content': this.view.qweb.render('kanban-box', this.qweb_context)
        });
        this.replaceElement($el);
        this.replace_fields();
    },
    replace_fields: function() {
        var self = this;
        this.$("field").each(function() {
            var $field = $(this);
            var $nfield = $("<span></span");
            var id = _.uniqueId("kanbanfield");
            self.fields[id] = $field;
            $nfield.attr("data-field_id", id);
            $field.replaceWith($nfield);
        });
    },
    add_widget: function($node) {
        var $orig = this.fields[$node.data("field_id")];
        var field = this.record[$orig.attr("name")];
        var type = field.type;
        type = $orig.attr("widget") ? $orig.attr("widget") : type;
        var obj = instance.web_kanban.fields_registry.get_object(type);
        var widget = new obj(this, field, $orig);
        this.sub_widgets.push(widget);
        widget.replace($node);
    },
    bind_events: function() {
        var self = this;
        this.setup_color_picker();
        this.$el.find('[title]').each(function(){
            //in case of kanban, attach tooltip to the element itself
            //otherwise it might stay on screen when kanban view reload
            //since default container is body.
            //(when clicking on ready for next stage for example)
            $(this).tooltip({
                delay: { show: 500, hide: 0},
                container: $(this),
                title: function() {
                    var template = $(this).attr('tooltip');
                    if (!self.view.qweb.has_template(template)) {
                        return false;
                    }
                    return self.view.qweb.render(template, self.qweb_context);
                },
            });
        });

        // If no draghandle is found, make the whole card as draghandle (provided one can edit)
        if (!this.$el.find('.oe_kanban_draghandle').length) {
            this.$el.children(':first')
                .toggleClass('oe_kanban_draghandle', this.view.is_action_enabled('edit'));
        }

        this.$el.find('.oe_kanban_action').click(function(ev) {
            ev.preventDefault();
            var $action = $(this),
                type = $action.data('type') || 'button',
                method = 'do_action_' + (type === 'action' ? 'object' : type);
            if ((type === 'edit' || type === 'delete') && ! self.view.is_action_enabled(type)) {
                self.view.open_record(self.id, true);
            } else if (_.str.startsWith(type, 'switch_')) {
                self.view.do_switch_view(type.substr(7));
            } else if (typeof self[method] === 'function') {
                self[method]($action);
            } else {
                self.do_warn("Kanban: no action for type : " + type);
            }
        });

        if (this.$el.find('.oe_kanban_global_click,.oe_kanban_global_click_edit').length) {
            this.$el.on('click', function(ev) {
                if (!ev.isTrigger && !$._data(ev.target, 'events')) {
                    var trigger = true;
                    var elem = ev.target;
                    var ischild = true;
                    var children = [];
                    while (elem) {
                        var events = $._data(elem, 'events');
                        if (elem == ev.currentTarget) {
                            ischild = false;
                        }
                        if (ischild) {
                            children.push(elem);
                            if (events && events.click) {
                                // do not trigger global click if one child has a click event registered
                                trigger = false;
                            }
                        }
                        if (trigger && events && events.click) {
                            _.each(events.click, function(click_event) {
                                if (click_event.selector) {
                                    // For each parent of original target, check if a
                                    // delegated click is bound to any previously found children
                                    _.each(children, function(child) {
                                        if ($(child).is(click_event.selector)) {
                                            trigger = false;
                                        }
                                    });
                                }
                            });
                        }
                        elem = elem.parentElement;
                    }
                    if (trigger) {
                        self.on_card_clicked(ev);
                    }
                }
            });
        }
    },
    /* actions when user click on the block with a specific class
     *  open on normal view : oe_kanban_global_click
     *  open on form/edit view : oe_kanban_global_click_edit
     */
    on_card_clicked: function(ev) {
        if(this.$el.find('.oe_kanban_global_click_edit').size()>0)
            this.do_action_edit();
        else
            this.do_action_open();
    },
    setup_color_picker: function() {
        var self = this;
        var $el = this.$el.find('ul.oe_kanban_colorpicker');
        if ($el.length) {
            $el.html(QWeb.render('KanbanColorPicker', {
                widget: this
            }));
            $el.on('click', 'a', function(ev) {
                ev.preventDefault();
                var color_field = $(this).parents('.oe_kanban_colorpicker').first().data('field') || 'color';
                var data = {};
                data[color_field] = $(this).data('color');
                self.view.dataset.write(self.id, data, {}).done(function() {
                    self.record[color_field] = $(this).data('color');
                    self.do_reload();
                });
            });
        }
    },
    do_action_delete: function($action) {
        var self = this;
        function do_it() {
            return $.when(self.view.dataset.unlink([self.id])).done(function() {
                self.group.remove_record(self.id);
                self.destroy();
            });
        }
        if (this.view.options.confirm_on_delete) {
            if (confirm(_t("Are you sure you want to delete this record ?"))) {
                return do_it();
            }
        } else
            return do_it();
    },
    do_action_edit: function($action) {
        this.view.open_record(this.id, true);
    },
    do_action_open: function($action) {
        this.view.open_record(this.id);
    },
    do_action_object: function ($action) {
        var button_attrs = $action.data();
        this.view.do_execute_action(button_attrs, this.view.dataset, this.id, this.do_reload);
    },
    do_reload: function() {
        var self = this;
        this.view.dataset.read_ids([this.id], this.view.fields_keys.concat(['__last_update'])).done(function(records) {
             _.each(self.sub_widgets, function(el) {
                 el.destroy();
             });
             self.sub_widgets = [];
            if (records.length) {
                self.set_record(records[0]);
                self.renderElement();
                self.init_content();
                self.group.compute_cards_auto_height();
                self.view.postprocess_m2m_tags();
            } else {
                self.destroy();
            }
        });
    },
    kanban_getcolor: function(variable) {
        var index = 0;
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
        var color = (index % this.view.number_of_color_schemes);
        return color;
    },
    kanban_color: function(variable) {
        var color = this.kanban_getcolor(variable);
        return color === '' ? '' : 'oe_kanban_color_' + color;
    },
    kanban_image: function(model, field, id, cache, options) {
        options = options || {};
        var url;
        if (this.record[field] && this.record[field].value && !instance.web.form.is_bin_size(this.record[field].value)) {
            url = 'data:image/png;base64,' + this.record[field].value;
        } else if (this.record[field] && ! this.record[field].value) {
            url = "/web/static/src/img/placeholder.png";
        } else {
            id = JSON.stringify(id);
            if (options.preview_image)
                field = options.preview_image;
            url = this.session.url('/web/binary/image', {model: model, field: field, id: id});
            if (cache !== undefined) {
                // Set the cache duration in seconds.
                url += '&cache=' + parseInt(cache, 10);
            }
        }
        return url;
    },
    kanban_text_ellipsis: function(s, size) {
        size = size || 160;
        if (!s) {
            return '';
        } else if (s.length <= size) {
            return s;
        } else {
            return s.substr(0, size) + '...';
        }
    },
    kanban_compute_domain: function(domain) {
        return instance.web.form.compute_domain(domain, this.values);
    }
});

/**
 * Quick creation view.
 *
 * Triggers a single event "added" with a single parameter "name", which is the
 * name entered by the user
 *
 * @class
 * @type {*}
 */
instance.web_kanban.QuickCreate = instance.web.Widget.extend({
    template: 'KanbanView.quick_create',
    
    /**
     * close_btn: If true, the widget will display a "Close" button able to trigger
     * a "close" event.
     */
    init: function(parent, dataset, context, buttons) {
        this._super(parent);
        this._dataset = dataset;
        this._buttons = buttons || false;
        this._context = context || {};
    },
    start: function () {
        var self = this;
        self.$input = this.$el.find('input');
        self.$input.keyup(function(event){
            if(event.keyCode == 13){
                self.quick_add();
            }
        });
        $(".oe_kanban_quick_create").focusout(function (e) {
            var val = self.$el.find('input').val();
            if (/^\s*$/.test(val)) { self.trigger('close'); }
            e.stopImmediatePropagation();
        });
        $(".oe_kanban_quick_create_add", this.$el).click(function () {
            self.quick_add();
            self.focus();
        });
        $(".oe_kanban_quick_create_close", this.$el).click(function (ev) {
            ev.preventDefault();
            self.trigger('close');
        });
        self.$input.keyup(function(e) {
            if (e.keyCode == 27 && self._buttons) {
                self.trigger('close');
            }
        });
    },
    focus: function() {
        this.$el.find('input').focus();
    },
    /**
     * Handles user event from nested quick creation view
     */
    quick_add: function () {
        var self = this;
        var val = this.$input.val();
        if (/^\s*$/.test(val)) { this.$el.remove(); return; }
        this._dataset.call(
            'name_create', [val, new instance.web.CompoundContext(
                    this._dataset.get_context(), this._context)])
            .then(function(record) {
                self.$input.val("");
                self.trigger('added', record[0]);
            }, function(error, event) {
                event.preventDefault();
                return self.slow_create();
            });
    },
    slow_create: function() {
        var self = this;
        var pop = new instance.web.form.SelectCreatePopup(this);
        pop.select_element(
            self._dataset.model,
            {
                title: _t("Create: ") + (this.string || this.name),
                initial_view: "form",
                disable_multiple_selection: true
            },
            [],
            {"default_name": self.$input.val()}
        );
        pop.on("elements_selected", self, function(element_ids) {
            self.$input.val("");
            self.trigger('added', element_ids[0]);
        });
    }
});

/**
 * Interface to be implemented by kanban fields.
 *
 */
instance.web_kanban.FieldInterface = {
    /**
        Constructor.
        - parent: The widget's parent.
        - field: A dictionary giving details about the field, including the current field's value in the
            raw_value field.
        - $node: The field <field> tag as it appears in the view, encapsulated in a jQuery object.
    */
    init: function(parent, field, $node) {},
};

/**
 * Abstract class for classes implementing FieldInterface.
 *
 * Properties:
 *     - value: useful property to hold the value of the field. By default, the constructor
 *     sets value property.
 *
 */
instance.web_kanban.AbstractField = instance.web.Widget.extend(instance.web_kanban.FieldInterface, {
    /**
        Constructor that saves the field and $node parameters and sets the "value" property.
    */
    init: function(parent, field, $node) {
        this._super(parent);
        this.field = field;
        this.$node = $node;
        this.options = instance.web.py_eval(this.$node.attr("options") || '{}');
        this.set("value", field.raw_value);
    },
});

instance.web_kanban.Priority = instance.web_kanban.AbstractField.extend({
    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name')
        this.parent = parent;
    },
    prepare_priority: function() {
        var self = this;
        var selection = this.field.selection || [];
        var init_value = selection && selection[0][0] || 0;
        var data = _.map(selection.slice(1), function(element, index) {
            var value = {
                'value': element[0],
                'name': element[1],
                'click_value': element[0],
            }
            if (index == 0 && self.get('value') == element[0]) {
                value['click_value'] = init_value;
            }
            return value;
        });
        return data;
    },
    renderElement: function() {
        var self = this;
        this.record_id = self.parent.id;
        this.priorities = self.prepare_priority();
        this.$el = $(QWeb.render("Priority", {'widget': this}));
        this.$el.find('.oe_legend').click(self.do_action.bind(self));
    },
    do_action: function(e) {
        var self = this;
        var li = $(e.target).closest( "li" );
        if (li.length) {
            var value = {};
            value[self.name] = String(li.data('value'));
            return self.parent.view.dataset._model.call('write', [[self.record_id], value, self.parent.view.dataset.get_context()]).done(self.reload_record.bind(self.parent));
        }
    },
    reload_record: function() {
        this.do_reload();
    },
});

instance.web_kanban.KanbanSelection = instance.web_kanban.AbstractField.extend({
    init: function(parent, field, $node) {
        this._super.apply(this, arguments);
        this.name = $node.attr('name')
        this.parent = parent;
    },
    prepare_dropdown_selection: function() {
        var data = [];
        _.map(this.field.selection || [], function(res) {
            var value = {
                'name': res[0],
                'tooltip': res[1],
                'state_name': res[1],
            }
            if (res[0] == 'normal') { value['state_class'] = 'oe_kanban_status'; }
            else if (res[0] == 'done') { value['state_class'] = 'oe_kanban_status oe_kanban_status_green'; }
            else { value['state_class'] = 'oe_kanban_status oe_kanban_status_red'; }
            data.push(value);
        });
        return data;
    },
    renderElement: function() {
        var self = this;
        this.record_id = self.parent.id;
        this.states = self.prepare_dropdown_selection();;
        this.$el = $(QWeb.render("KanbanSelection", {'widget': self}));
        this.$el.find('.oe_legend').click(self.do_action.bind(self));
    },
    do_action: function(e) {
        var self = this;
        var li = $(e.target).closest( "li" );
        if (li.length) {
            var value = {};
            value[self.name] = String(li.data('value'));
            return self.parent.view.dataset._model.call('write', [[self.record_id], value, self.parent.view.dataset.get_context()]).done(self.reload_record.bind(self.parent));
        }
    },
    reload_record: function() {
        this.do_reload();
    },
});

instance.web_kanban.fields_registry = new instance.web.Registry({});
instance.web_kanban.fields_registry.add('priority','instance.web_kanban.Priority');
instance.web_kanban.fields_registry.add('kanban_state_selection','instance.web_kanban.KanbanSelection');
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
