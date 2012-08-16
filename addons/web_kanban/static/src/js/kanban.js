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
        this.limit = options.limit || 80;
        this.add_group_mutex = new $.Mutex();
    },
    destroy: function() {
        this._super.apply(this, arguments);
        $('html').off('click.kanban');
    },
    on_loaded: function(data) {
        this.fields_view = data;
        this.$element.addClass(this.fields_view.arch.attrs['class']);
        this.$buttons = $(QWeb.render("KanbanView.buttons", {'widget': this}));
        if (this.options.$buttons) {
            this.$buttons.appendTo(this.options.$buttons);
        } else {
            this.$element.find('.oe_kanban_buttons').replaceWith(this.$buttons);
        }
        this.$buttons
            .on('click','button.oe_kanban_button_new', this.do_add_record);
        this.$groups = this.$element.find('.oe_kanban_groups tr');
        this.fields_keys = _.keys(this.fields_view.fields);
        this.add_qweb_template();
        this.has_been_loaded.resolve();
        return $.when();
    },
    _is_quick_create_enabled: function() {
        if (! this.options.quick_creatable)
            return false;
        if (this.fields_view.arch.attrs.quick_create !== undefined)
            return JSON.parse(this.fields_view.arch.attrs.quick_create);
        return !! this.group_by;
    },
    _is_action_enabled: function(action) {
        if (! this.options.creatable)
            return false;
        if (_.has(this.fields_view.arch.attrs, action))
            return JSON.parse(this.fields_view.arch.attrs[action]);
        return true;
    },
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
                node.tag = QWeb.prefix;
                node.attrs[QWeb.prefix + '-esc'] = 'record.' + node.attrs['name'] + '.value';
                this.extract_aggregates(node);
                break;
            case 'button':
            case 'a':
                var type = node.attrs.type || '';
                if (_.indexOf('action,object,edit,delete'.split(','), type) !== -1) {
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
    do_search: function(domain, context, group_by) {
        var self = this;
        this.$element.find('.oe_view_nocontent').remove();
        this.search_domain = domain;
        this.search_context = context;
        this.search_group_by = group_by;
        $.when(this.has_been_loaded).then(function() {
            self.group_by = group_by.length ? group_by[0] : self.fields_view.arch.attrs.default_group_by;
            self.datagroup = new instance.web.DataGroup(self, self.dataset.model, domain, context, self.group_by ? [self.group_by] : []);
            self.datagroup.list(self.fields_keys, self.do_process_groups, self.do_process_dataset);
        });
    },
    do_process_groups: function(groups) {
        var self = this;
        this.$element.remove('oe_kanban_ungrouped').addClass('oe_kanban_grouped');
        this.add_group_mutex.exec(function() {
            self.do_clear_groups();
            self.dataset.ids = [];
            var remaining = groups.length - 1,
                groups_array = [];
            return $.when.apply(null, _.map(groups, function (group, index) {
                var dataset = new instance.web.DataSetSearch(self, self.dataset.model,
                    new instance.web.CompoundContext(self.dataset.get_context(), group.context), group.domain);
                return dataset.read_slice(self.fields_keys.concat(['__last_update']), { 'limit': self.limit })
                    .pipe(function(records) {
                        self.dataset.ids.push.apply(self.dataset.ids, dataset.ids);
                        groups_array[index] = new instance.web_kanban.KanbanGroup(self, records, group, dataset);
                        if (!remaining--) {
                            self.dataset.index = self.dataset.size() ? 0 : null;
                            return self.do_add_groups(groups_array);
                        }
                });
            }));
        });
    },
    do_process_dataset: function(dataset) {
        var self = this;
        this.$element.remove('oe_kanban_grouped').addClass('oe_kanban_ungrouped');
        this.add_group_mutex.exec(function() {
            var def = $.Deferred();
            self.do_clear_groups();
            self.dataset.read_slice(self.fields_keys.concat(['__last_update']), { 'limit': self.limit }).then(function(records) {
                var kgroup = new instance.web_kanban.KanbanGroup(self, records, null, self.dataset);
                self.do_add_groups([kgroup]).then(function() {
                    if (_.isEmpty(records)) {
                        self.no_result();
                    }
                    def.resolve();
                });
            }).then(null, function() {
                def.reject();
            });
            return def;
        });
    },
    do_reload: function() {
        this.do_search(this.search_domain, this.search_context, this.search_group_by);
    },
    do_clear_groups: function() {
        _.each(this.groups, function(group) {
            group.destroy();
        });
        this.groups = [];
    },
    do_add_groups: function(groups) {
        var self = this;
        _.each(groups, function(group) {
            self.groups[group.undefined_title ? 'unshift' : 'push'](group);
        });
        var groups_started = _.map(this.groups, function(group) {
            return group.insertBefore(self.$element.find('.oe_kanban_groups_headers td:last'));
        });
        return $.when.apply(null, groups_started).then(function () {
            self.on_groups_started();
        });
    },
    on_groups_started: function() {
        var self = this;
        this.compute_groups_width();
        if (this.group_by) {
            this.$element.find('.oe_kanban_column').sortable({
                connectWith: '.oe_kanban_column',
                handle : '.oe_kanban_draghandle',
                start: function(event, ui) {
                    self.currently_dragging.index = ui.item.index();
                    self.currently_dragging.group = ui.item.parents('.oe_kanban_column:first').data('widget');
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
        var self = this;
        $.fn.tipsy.clear();
        $(old_group.$element).add(new_group.$element).find('.oe_kanban_aggregates, .oe_kanban_group_length').hide();
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
            this.dataset.write(record.id, data, {}, function() {
                record.do_reload();
                new_group.do_save_sequences();
            }).fail(function(error, evt) {
                evt.preventDefault();
                alert("An error has occured while moving the record to this group.");
                self.do_reload(); // TODO: use draggable + sortable in order to cancel the dragging when the rcp fails
            });
        }
    },
    compute_groups_width: function() {
        var unfolded = 0;
        var self = this;
        _.each(this.groups, function(group) {
            unfolded += group.state.folded ? 0 : 1;
            group.$element.css('width', '');
        });
        _.each(this.groups, function(group) {
            if (!group.state.folded) {
                if (182*unfolded>=self.$element.width()) {
                    group.$element.children(':first').css('width', "170px");
                } else if (262*unfolded<self.$element.width()) {
                    group.$element.children(':first').css('width', "250px");
                } else {
		    // -12 because of padding 6 between cards
		    // -1 because of the border of the latest dummy column
                    group.$element.children(':first').css('width', Math.floor((self.$element.width()-1)/unfolded)-12 + 'px');
                }
            }
        });
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
            this.do_switch_view('form', null, { editable: editable });
        } else {
            this.do_warn("Kanban: could not find id#" + id);
        }
    },
    no_result: function() {
        if (this.groups.group_by
            || !this.options.action
            || !this.options.action.help) {
            return;
        }
        this.$element.find('.oe_view_nocontent').remove();
        this.$element.prepend(
            $('<div class="oe_view_nocontent">').html(this.options.action.help)
        );
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
            this.value = group.value;
            this.title = group.value;
            if (this.value instanceof Array) {
                this.title = this.value[1];
                this.value = this.value[0];
            }
            var field = this.view.fields_view.fields[this.view.group_by];
            if (field) {
                try {
                    this.title = instance.web.format_value(group.value, field, false);
                } catch(e) {}
            }
            _.each(this.view.aggregates, function(value, key) {
                self.aggregates[value] = group.aggregates[key];
            });
        }

        if (this.title === false) {
            this.title = _t('Undefined');
            this.undefined_title = true;
        }
        var key = this.view.group_by + '-' + this.value;
        if (!this.view.state.groups[key]) {
            this.view.state.groups[key] = {
                folded: false
            };
        }
        this.state = this.view.state.groups[key];
        this.$records = null;

        this.records = [];
        this.$has_been_started.then(function() {
            self.do_add_records(records);
        });
    },
    start: function() {
        var self = this,
            def = this._super();
        if (! self.view.group_by) {
            self.$element.addClass("oe_kanban_no_group");
            self.quick = new (get_class(self.view.quick_create_class))(this, self.dataset, {}, false)
                .on('added', self, self.proxy('quick_created'));
            self.quick.replace($(".oe_kanban_no_group_qc_placeholder"));
        }
        this.$records = $(QWeb.render('KanbanView.group_records_container', { widget : this}));
        this.$records.insertBefore(this.view.$element.find('.oe_kanban_groups_records td:last'));
        this.$element.find(".oe_kanban_fold_icon").click(function() {
            self.do_toggle_fold();
            self.view.compute_groups_width();
            return false;
        });
        this.$element.find('.oe_kanban_add').click(function () {
            if (self.quick) { return; }
            var ctx = {};
            ctx['default_' + self.view.group_by] = self.value;
            self.quick = new (get_class(self.view.quick_create_class))(this, self.dataset, ctx, true)
                .on('added', self, self.proxy('quick_created'))
                .on('close', self, function() {
                    this.quick.destroy();
                    delete this.quick;
                });
            self.quick.appendTo($(".oe_kanban_group_list_header", self.$records));
            self.quick.focus();
        });
        // Add bounce effect on image '+' of kanban header when click on empty space of kanban grouped column.
        var add_btn = this.$element.find('.oe_kanban_add');
        this.$records.find('.oe_kanban_show_more').click(this.do_show_more);
        if (this.state.folded) {
            this.do_toggle_fold();
        }
        this.$element.data('widget', this);
        this.$records.data('widget', this);
        this.$has_been_started.resolve();
        this.compute_cards_auto_height();
        this.$records.click(function (ev) {
            if (ev.target == ev.currentTarget) {
                if (!self.state.folded) {
                    add_btn.effect('bounce', {distance: 18, times: 5}, 150)
                } 
            }
        });
        return def;
    },
    compute_cards_auto_height: function() {
        // oe_kanban_auto_height is an empty class used by the kanban view in order
        // to normalize height amongst kanban cards. (by group)
        var self = this;
        var min_height = 0;
        var els = [];
        _.each(this.records, function(r) {
            var $e = r.$element.find('.oe_kanban_auto_height').first().css('min-height', 0);
            if ($e.length) {
                els.push($e[0]);
                min_height = Math.max(min_height, $e.outerHeight());
            }
        });
        $(els).css('min-height', min_height);
    },
    destroy: function() {
        this._super();
        if (this.$records) {
            this.$records.remove();
        }
    },
    do_show_more: function(evt) {
        var self = this;
        this.dataset.read_slice(this.view.fields_keys.concat(['__last_update']), {
            'limit': self.view.limit,
            'offset': self.dataset_offset += self.view.limit
        }).then(this.do_add_records);
    },
    do_add_records: function(records, prepend) {
        var self = this;
        _.each(records, function(record) {
            var rec = new instance.web_kanban.KanbanRecord(self, record);
            if (!prepend) {
                rec.insertBefore(self.$records.find('.oe_kanban_show_more'));
                self.records.push(rec);
            } else {
                rec.insertAfter($(".oe_kanban_group_list_header", self.$records));
                self.records.unshift(rec);
            }
        });
        this.$records.find('.oe_kanban_show_more').toggle(this.records.length < this.dataset.size())
            .find('.oe_kanban_remaining').text(this.dataset.size() - this.records.length);
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
        this.$element.add(this.$records).toggleClass('oe_kanban_group_folded');
        this.state.folded = this.$element.is('.oe_kanban_group_folded');
    },
    do_save_sequences: function() {
        var self = this;
        if (_.indexOf(this.view.fields_keys, 'sequence') > -1) {
            _.each(this.records, function(record, index) {
                self.view.dataset.write(record.id, { sequence : index });
            });
        }
    },
    /**
     * Handles a newly created record
     *
     * @param {id} id of the newly created record
     */
    quick_created: function (record) {
        var id = record, self = this;
        this.dataset.read_ids([id], this.view.fields_keys)
            .then(function (records) {
                self.view.dataset.ids.push(id);
                self.do_add_records(records, true);
            });
    },
    _is_action_enabled: function(action) {
        if (_.has(this.fields_view.arch.attrs, action))
            return JSON.parse(this.fields_view.arch.attrs[action]);
        return true;
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
        this._super();
        this.$element.data('widget', this);
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
    },
    bind_events: function() {
        var self = this;
        this.setup_color_picker();
        var $show_on_click = self.$element.find('.oe_kanban_box_show_onclick');
        $show_on_click.toggle(this.state.folded);
        this.$element.find('.oe_kanban_box_show_onclick_trigger').click(function() {
            $show_on_click.toggle();
            self.state.folded = !self.state.folded;
        });

        this.$element.find('[tooltip]').tipsy({
            delayIn: 500,
            delayOut: 0,
            fade: true,
            title: function() {
                var template = $(this).attr('tooltip');
                if (!self.view.qweb.has_template(template)) {
                    return false;
                }
                return self.view.qweb.render(template, self.qweb_context);
            },
            gravity: 's',
            html: true,
            opacity: 0.8,
            trigger: 'hover'
        });

        // If no draghandle is found, make the whole card as draghandle
        if (!this.$element.find('.oe_kanban_draghandle').length) {
            this.$element.children(':first').addClass('oe_kanban_draghandle');
        }

        this.$element.find('.oe_kanban_action').click(function() {
            var $action = $(this),
                type = $action.data('type') || 'button',
                method = 'do_action_' + (type === 'action' ? 'object' : type);
            if (_.str.startsWith(type, 'switch_')) {
                self.view.do_switch_view(type.substr(7));
            } else if (typeof self[method] === 'function') {
                self[method]($action);
            } else {
                self.do_warn("Kanban: no action for type : " + type);
            }
        });

        if (this.$element.find('.oe_kanban_global_click').length) {
            this.$element.on('click', function(ev) {
                if (!ev.isTrigger && !$(ev.target).data('events')) {
                    var trigger = true;
                    var elem = ev.target;
                    var ischild = true;
                    var children = [];
                    while (elem) {
                        var events = $(elem).data('events');
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
    on_card_clicked: function(ev) {
        this.view.open_record(this.id);
    },
    setup_color_picker: function() {
        var self = this;
        var $el = this.$element.find('ul.oe_kanban_colorpicker');
        if ($el.length) {
            $el.html(QWeb.render('KanbanColorPicker', {
                widget: this
            }));
            $el.on('click', 'a', function(ev) {
                ev.preventDefault();
                var color_field = $(this).parents('.oe_kanban_colorpicker').first().data('field') || 'color';
                var data = {};
                data[color_field] = $(this).data('color');
                self.view.dataset.write(self.id, data, {}, function() {
                    self.record[color_field] = $(this).data('color');
                    self.do_reload();
                });
            });
        }
    },
    do_action_delete: function($action) {
        var self = this;
        function do_it() {
            return $.when(self.view.dataset.unlink([self.id])).then(function() {
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
    do_action_object: function ($action) {
        var button_attrs = $action.data();
        this.view.do_execute_action(button_attrs, this.view.dataset, this.id, this.do_reload);
    },
    do_reload: function() {
        var self = this;
        this.view.dataset.read_ids([this.id], this.view.fields_keys.concat(['__last_update'])).then(function(records) {
            if (records.length) {
                self.set_record(records[0]);
                self.replaceElement($(self.render()));
                self.$element.data('widget', self);
                self.bind_events();
                self.group.compute_cards_auto_height();
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
    kanban_gravatar: function(email, size) {
        size = size || 22;
        email = _.str.trim(email || '').toLowerCase();
        var default_ = _.str.isBlank(email) ? 'mm' : 'identicon';
        var email_md5 = $.md5(email);
        return 'http://www.gravatar.com/avatar/' + email_md5 + '.png?s=' + size + '&d=' + default_;
    },
    kanban_image: function(model, field, id, cache) {
        var url;
        if (this.record[field] && this.record[field].value && ! /^\d+(\.\d*)? \w+$/.test(this.record[field].value)) {
            url = 'data:image/png;base64,' + this.record[field].value;
        } else if (this.record[field] && ! this.record[field].value) {
            url = "/web/static/src/img/placeholder.png";
        } else {
            id = escape(JSON.stringify(id));
            url = instance.session.prefix + '/web/binary/image?session_id=' + this.session.session_id + '&model=' + model + '&field=' + field + '&id=' + id;
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
    },
    _is_action_enabled: function(action) {
        return (_.has(this.fields_view.arch.attrs, action))?JSON.parse(this.fields_view.arch.attrs[action]):true;
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
        self.$input = this.$element.find('input');
        self.$input.keyup(function(event){
            if(event.keyCode == 13){
                self.quick_add();
            }
        });
        $(".oe_kanban_quick_create_add", this.$element).click(function () {
            self.quick_add();
        });
        $(".oe_kanban_quick_create_close", this.$element).click(function () {
            self.trigger('close');
        });
        self.$input.keyup(function(e) {
            if (e.keyCode == 27 && self._buttons) {
                self.trigger('close');
            }
        });
    },
    focus: function() {
        this.$element.find('input').focus();
    },
    /**
     * Handles user event from nested quick creation view
     */
    quick_add: function () {
        var self = this;
        this._dataset.call(
            'name_create', [self.$input.val(), new instance.web.CompoundContext(
                    this._dataset.get_context(), this._context)])
            .pipe(function(record) {
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
        pop.on_select_elements.add(function(element_ids) {
            self.$input.val("");
            self.trigger('added', element_ids[0]);
        });
    }
});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
