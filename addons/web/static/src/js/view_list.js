openerp.web.list = function (instance) {
var _t = instance.web._t,
   _lt = instance.web._lt;
var QWeb = instance.web.qweb;
instance.web.views.add('list', 'instance.web.ListView');
instance.web.ListView = instance.web.View.extend( /** @lends instance.web.ListView# */ {
    _template: 'ListView',
    display_name: _lt('List'),
    defaults: {
        // records can be selected one by one
        'selectable': true,
        // list rows can be deleted
        'deletable': false,
        // whether the column headers should be displayed
        'header': true,
        // display addition button, with that label
        'addable': _lt("Create"),
        // whether the list view can be sorted, note that once a view has been
        // sorted it can not be reordered anymore
        'sortable': true,
        // whether the view rows can be reordered (via vertical drag & drop)
        'reorderable': true,
        'action_buttons': true,
        // if true, the view can't be editable, ignoring the view's and the context's
        // instructions
        'read_only': false,
        // if true, the 'Import', 'Export', etc... buttons will be shown
        'import_enabled': true,
    },
    /**
     * Core class for list-type displays.
     *
     * As a view, needs a number of view-related parameters to be correctly
     * instantiated, provides options and overridable methods for behavioral
     * customization.
     *
     * See constructor parameters and method documentations for information on
     * the default behaviors and possible options for the list view.
     *
     * @constructs instance.web.ListView
     * @extends instance.web.View
     *
     * @param parent parent object
     * @param {instance.web.DataSet} dataset the dataset the view should work with
     * @param {String} view_id the listview's identifier, if any
     * @param {Object} options A set of options used to configure the view
     * @param {Boolean} [options.selectable=true] determines whether view rows are selectable (e.g. via a checkbox)
     * @param {Boolean} [options.header=true] should the list's header be displayed
     * @param {Boolean} [options.deletable=true] are the list rows deletable
     * @param {void|String} [options.addable="New"] should the new-record button be displayed, and what should its label be. Use ``null`` to hide the button.
     * @param {Boolean} [options.sortable=true] is it possible to sort the table by clicking on column headers
     * @param {Boolean} [options.reorderable=true] is it possible to reorder list rows
     */
    init: function(parent, dataset, view_id, options) {
        var self = this;
        this._super(parent);
        this.set_default_options(_.extend({}, this.defaults, options || {}));
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.previous_colspan = null;
        this.colors = null;
        this.fonts = null;

        this.columns = [];

        this.records = new Collection();

        this.set_groups(new (this.options.GroupsType)(this));

        if (this.dataset instanceof instance.web.DataSetStatic) {
            this.groups.datagroup = new instance.web.StaticDataGroup(this.dataset);
        } else {
            this.groups.datagroup = new instance.web.DataGroup(
                this, this.model,
                dataset.get_domain(),
                dataset.get_context());
            this.groups.datagroup.sort = this.dataset._sort;
        }

        this.page = 0;
        this.records.bind('change', function (event, record, key) {
            if (!_(self.aggregate_columns).chain()
                    .pluck('name').contains(key).value()) {
                return;
            }
            self.compute_aggregates();
        });

        this.no_leaf = false;
    },
    set_default_options: function (options) {
        this._super(options);
        _.defaults(this.options, {
            GroupsType: instance.web.ListView.Groups,
            ListType: instance.web.ListView.List
        });
    },

    /**
     * Retrieves the view's number of records per page (|| section)
     *
     * options > defaults > parent.action.limit > indefinite
     *
     * @returns {Number|null}
     */
    limit: function () {
        if (this._limit === undefined) {
            this._limit = (this.options.limit
                        || this.defaults.limit
                        || (this.getParent().action || {}).limit
                        || 80);
        }
        return this._limit;
    },
    /**
     * Set a custom Group construct as the root of the List View.
     *
     * @param {instance.web.ListView.Groups} groups
     */
    set_groups: function (groups) {
        var self = this;
        if (this.groups) {
            $(this.groups).unbind("selected deleted action row_link");
            delete this.groups;
        }

        this.groups = groups;
        $(this.groups).bind({
            'selected': function (e, ids, records) {
                self.do_select(ids, records);
            },
            'deleted': function (e, ids) {
                self.do_delete(ids);
            },
            'action': function (e, action_name, id, callback) {
                self.do_button_action(action_name, id, callback);
            },
            'row_link': function (e, id, dataset, view) {
                self.do_activate_record(dataset.index, id, dataset, view);
            }
        });
    },
    /**
     * View startup method, the default behavior is to set the ``oe_list``
     * class on its root element and to perform an RPC load call.
     *
     * @returns {$.Deferred} loading promise
     */
    start: function() {
        this.$element.addClass('oe_list');
        return this.reload_view(null, null, true);
    },
    /**
     * Returns the style for the provided record in the current view (from the
     * ``@colors`` and ``@fonts`` attributes)
     *
     * @param {Record} record record for the current row
     * @returns {String} CSS style declaration
     */
    style_for: function (record) {
        var style= '';

        var context = _.extend({}, record.attributes, {
            uid: this.session.uid,
            current_date: new Date().toString('yyyy-MM-dd')
            // TODO: time, datetime, relativedelta
        });

        if (this.fonts) {
            for(var i=0, len=this.fonts.length; i<len; ++i) {
                var pair = this.fonts[i],
                font = pair[0],
                expression = pair[1];
                if (py.evaluate(expression, context).toJSON()) {
                    switch(font) {
                    case 'bold':
                        style += 'font-weight: bold;';
                        break;
                    case 'italic':
                        style += 'font-style: italic;';
                        break;
                    case 'underline':
                        style += 'text-decoration: underline;';
                        break;
                    }
                }
            }
        }

        if (!this.colors) { return style; }
        for(var i=0, len=this.colors.length; i<len; ++i) {
            var pair = this.colors[i],
                color = pair[0],
                expression = pair[1];
            if (py.evaluate(expression, context).toJSON()) {
                return style += 'color: ' + color + ';';
            }
            // TODO: handle evaluation errors
        }
        return style;
    },
    /**
     * Called after loading the list view's description, sets up such things
     * as the view table's columns, renders the table itself and hooks up the
     * various table-level and row-level DOM events (action buttons, deletion
     * buttons, selection of records, [New] button, selection of a given
     * record, ...)
     *
     * Sets up the following:
     *
     * * Processes arch and fields to generate a complete field descriptor for each field
     * * Create the table itself and allocate visible columns
     * * Hook in the top-level (header) [New|Add] and [Delete] button
     * * Sets up showing/hiding the top-level [Delete] button based on records being selected or not
     * * Sets up event handlers for action buttons and per-row deletion button
     * * Hooks global callback for clicking on a row
     * * Sets up its sidebar, if any
     *
     * @param {Object} data wrapped fields_view_get result
     * @param {Object} data.fields_view fields_view_get result (processed)
     * @param {Object} data.fields_view.fields mapping of fields for the current model
     * @param {Object} data.fields_view.arch current list view descriptor
     * @param {Boolean} grouped Is the list view grouped
     */
    on_loaded: function(data, grouped) {
        var self = this;
        this.fields_view = data;
        this.name = "" + this.fields_view.arch.attrs.string;

        if (this.fields_view.arch.attrs.colors) {
            this.colors = _(this.fields_view.arch.attrs.colors.split(';')).chain()
                .compact()
                .map(function(color_pair) {
                    var pair = color_pair.split(':'),
                        color = pair[0],
                        expr = pair[1];
                    return [color, py.parse(py.tokenize(expr)), expr];
                }).value();
        }

        if (this.fields_view.arch.attrs.fonts) {
            this.fonts = _(this.fields_view.arch.attrs.fonts.split(';')).chain().compact()
                .map(function(font_pair) {
                    var pair = font_pair.split(':'),
                        font = pair[0],
                        expr = pair[1];
                    return [font, py.parse(py.tokenize(expr)), expr];
                }).value();
        }

        this.setup_columns(this.fields_view.fields, grouped);

        this.$element.html(QWeb.render(this._template, this));
        this.$element.addClass(this.fields_view.arch.attrs['class']);
        // Head hook
        // Selecting records
        this.$element.find('.oe_list_record_selector').click(function(){
            self.$element.find('.oe_list_record_selector input').prop('checked',
                self.$element.find('.oe_list_record_selector').prop('checked')  || false);
            var selection = self.groups.get_selection();
            $(self.groups).trigger(
                'selected', [selection.ids, selection.records]);
        });

        // Sorting columns
        this.$element.find('thead').delegate('th.oe_sortable[data-id]', 'click', function (e) {
            e.stopPropagation();
            var $this = $(this);
            self.dataset.sort($this.data('id'));
            if($this.hasClass("sortdown") || $this.hasClass("sortup"))  {
                $this.toggleClass("sortdown").toggleClass("sortup");
            } else {
                $this.toggleClass("sortdown");
            }
            $this.siblings('.oe_sortable').removeClass("sortup sortdown");

            self.reload_content();
        });

        // Add button and Import link
        if (!this.$buttons) {
            this.$buttons = $(QWeb.render("ListView.buttons", {'widget':self}));
            if (this.options.$buttons) {
                this.$buttons.appendTo(this.options.$buttons);
            } else {
                this.$element.find('.oe_list_buttons').replaceWith(this.$buttons);
            }
            this.$buttons.find('.oe_list_add')
                    .click(this.proxy('do_add_record'))
                    .prop('disabled', grouped);
            this.$buttons.on('click', '.oe_list_button_import', function() {
                self.on_sidebar_import();
                return false;
            });
        }

        // Pager
        if (!this.$pager) {
            this.$pager = $(QWeb.render("ListView.pager", {'widget':self}));
            if (this.options.$buttons) {
                this.$pager.appendTo(this.options.$pager);
            } else {
                this.$element.find('.oe_list_pager').replaceWith(this.$pager);
            }

            this.$pager
                .on('click', 'a[data-pager-action]', function () {
                    var $this = $(this);
                    var max_page = Math.floor(self.dataset.size() / self.limit());
                    switch ($this.data('pager-action')) {
                        case 'first':
                            self.page = 0; break;
                        case 'last':
                            self.page = max_page - 1;
                            break;
                        case 'next':
                            self.page += 1; break;
                        case 'previous':
                            self.page -= 1; break;
                    }
                    if (self.page < 0) {
                        self.page = max_page;
                    } else if (self.page > max_page) {
                        self.page = 0;
                    }
                    self.reload_content();
                }).find('.oe_list_pager_state')
                    .click(function (e) {
                        e.stopPropagation();
                        var $this = $(this);

                        var $select = $('<select>')
                            .appendTo($this.empty())
                            .click(function (e) {e.stopPropagation();})
                            .append('<option value="80">80</option>' +
                                    '<option value="100">100</option>' +
                                    '<option value="200">200</option>' +
                                    '<option value="500">500</option>' +
                                    '<option value="NaN">' + _t("Unlimited") + '</option>')
                            .change(function () {
                                var val = parseInt($select.val(), 10);
                                self._limit = (isNaN(val) ? null : val);
                                self.page = 0;
                                self.reload_content();
                            }).blur(function() {
                                $(this).trigger('change');
                            })
                            .val(self._limit || 'NaN');
                    });
        }

        // Sidebar
        if (!this.sidebar && this.options.$sidebar) {
            this.sidebar = new instance.web.Sidebar(this);
            this.sidebar.appendTo(this.options.$sidebar);
            this.sidebar.add_items('other', [
                { label: _t("Import"), callback: this.on_sidebar_import },
                { label: _t("Export"), callback: this.on_sidebar_export },
                { label: _t('Delete'), callback: this.do_delete_selected },
            ]);
            this.sidebar.add_toolbar(this.fields_view.toolbar);
        }
    },
    /**
     * Configures the ListView pager based on the provided dataset's information
     *
     * Horrifying side-effect: sets the dataset's data on this.dataset?
     *
     * @param {instance.web.DataSet} dataset
     */
    configure_pager: function (dataset) {
        this.dataset.ids = dataset.ids;
        // Not exactly clean
        if (dataset._length) {
            this.dataset._length = dataset._length;
        }

        var total = dataset.size();
        var limit = this.limit() || total;
        this.$pager.toggleClass('oe_list_pager_single_page', (total <= limit));
        var spager = '-';
        if (total) {
            var range_start = this.page * limit + 1;
            var range_stop = range_start - 1 + limit;
            if (range_stop > total) {
                range_stop = total;
            }
            spager = _.str.sprintf('%d-%d of %d', range_start, range_stop, total);
        }

        this.$pager.find('.oe_list_pager_state').text(spager);
    },
    /**
     * Sets up the listview's columns: merges view and fields data, move
     * grouped-by columns to the front of the columns list and make them all
     * visible.
     *
     * @param {Object} fields fields_view_get's fields section
     * @param {Boolean} [grouped] Should the grouping columns (group and count) be displayed
     */
    setup_columns: function (fields, grouped) {
        var domain_computer = instance.web.form.compute_domain;

        var noop = function () { return {}; };
        var field_to_column = function (field) {
            var name = field.attrs.name;
            var column = _.extend({id: name, tag: field.tag},
                    fields[name], field.attrs);
            // modifiers computer
            if (column.modifiers) {
                var modifiers = JSON.parse(column.modifiers);
                column.modifiers_for = function (fields) {
                    var out = {};

                    for (var attr in modifiers) {
                        if (!modifiers.hasOwnProperty(attr)) { continue; }
                        var modifier = modifiers[attr];
                        out[attr] = _.isBoolean(modifier)
                            ? modifier
                            : domain_computer(modifier, fields);
                    }

                    return out;
                };
                if (modifiers['tree_invisible']) {
                    column.invisible = '1';
                } else {
                    delete column.invisible;
                }
                column.modifiers = modifiers;
            } else {
                column.modifiers_for = noop;
                column.modifiers = {};
            }
            return column;
        };

        this.columns.splice(0, this.columns.length);
        this.columns.push.apply(
                this.columns,
                _(this.fields_view.arch.children).map(field_to_column));
        if (grouped) {
            this.columns.unshift({
                id: '_group', tag: '', string: _t("Group"), meta: true,
                modifiers_for: function () { return {}; },
                modifiers: {}
            }, {
                id: '_count', tag: '', string: '#', meta: true,
                modifiers_for: function () { return {}; },
                modifiers: {}
            });
        }

        this.visible_columns = _.filter(this.columns, function (column) {
            return column.invisible !== '1';
        });

        this.aggregate_columns = _(this.visible_columns)
            .map(function (column) {
                if (column.type !== 'integer' && column.type !== 'float') {
                    return {};
                }
                var aggregation_func = column['group_operator'] || 'sum';
                if (!(aggregation_func in column)) {
                    return {};
                }

                return _.extend({}, column, {
                    'function': aggregation_func,
                    label: column[aggregation_func]
                });
            });
    },
    /**
     * Used to handle a click on a table row, if no other handler caught the
     * event.
     *
     * The default implementation asks the list view's view manager to switch
     * to a different view (by calling
     * :js:func:`~instance.web.ViewManager.on_mode_switch`), using the
     * provided record index (within the current list view's dataset).
     *
     * If the index is null, ``switch_to_record`` asks for the creation of a
     * new record.
     *
     * @param {Number|void} index the record index (in the current dataset) to switch to
     * @param {String} [view="page"] the view type to switch to
     */
    select_record:function (index, view) {
        view = view || index == null ? 'form' : 'form';
        this.dataset.index = index;
        _.delay(_.bind(function () {
            this.do_switch_view(view);
        }, this));
    },
    do_show: function () {
        this._super();
        if (this.sidebar) {
            this.sidebar.$element.show();
        }
        if (this.$buttons) {
            this.$buttons.show();
        }
        if (this.$pager) {
            this.$pager.show();
        }
    },
    do_hide: function () {
        if (this.sidebar) {
            this.sidebar.$element.hide();
        }
        if (this.$buttons) {
            this.$buttons.hide();
        }
        if (this.$pager) {
            this.$pager.hide();
        }
        this._super();
    },
    /**
     * Reloads the list view based on the current settings (dataset & al)
     *
     * @param {Boolean} [grouped] Should the list be displayed grouped
     * @param {Object} [context] context to send the server while loading the view
     */
    reload_view: function (grouped, context, initial) {
        var self = this;
        var callback = function (field_view_get) {
            self.on_loaded(field_view_get, grouped);
        };
        if (this.embedded_view) {
            return $.Deferred().then(callback).resolve(this.embedded_view);
        } else {
            return this.rpc('/web/listview/load', {
                model: this.model,
                view_id: this.view_id,
                view_type: "tree",
                context: this.dataset.get_context(context),
                toolbar: !!this.options.$sidebar
            }, callback);
        }
    },
    /**
     * re-renders the content of the list view
     *
     * @returns {$.Deferred} promise to content reloading
     */
    reload_content: function () {
        var self = this;
        self.$element.find('.oe_list_record_selector').prop('checked', false);
        this.records.reset();
        var reloaded = $.Deferred();
        this.$element.find('.oe_list_content').append(
            this.groups.render(function () {
                if (self.dataset.index == null) {
                    var has_one = false;
                    self.records.each(function () { has_one = true; });
                    if (has_one) {
                        self.dataset.index = 0;
                    }
                }
                self.compute_aggregates();
                reloaded.resolve();
            }));
        this.do_push_state({
            page: this.page,
            limit: this._limit
        });
        return reloaded.promise();
    },
    reload: function () {
        return this.reload_content();
    },
    reload_record: function (record) {
        return this.dataset.read_ids(
            [record.get('id')],
            _.pluck(_(this.columns).filter(function (r) {
                    return r.tag === 'field';
                }), 'name')
        ).then(function (records) {
            _(records[0]).each(function (value, key) {
                record.set(key, value, {silent: true});
            });
            record.trigger('change', record);
        });
    },

    do_load_state: function(state, warm) {
        var reload = false;
        if (state.page && this.page !== state.page) {
            this.page = state.page;
            reload = true;
        }
        if (state.limit) {
            if (_.isString(state.limit)) {
                state.limit = null;
            }
            if (state.limit !== this._limit) {
                this._limit = state.limit;
                reload = true;
            }
        }
        if (reload) {
            this.reload_content();
        }
    },
    /**
     * Handler for the result of eval_domain_and_context, actually perform the
     * searching
     *
     * @param {Object} results results of evaluating domain and process for a search
     */
    do_search: function (domain, context, group_by) {
        this.page = 0;
        this.groups.datagroup = new instance.web.DataGroup(
            this, this.model, domain, context, group_by);
        this.groups.datagroup.sort = this.dataset._sort;

        if (_.isEmpty(group_by) && !context['group_by_no_leaf']) {
            group_by = null;
        }
        this.no_leaf = !!context['group_by_no_leaf'];

        this.reload_view(!!group_by, context).then(
            this.proxy('reload_content'));
    },
    /**
     * Handles the signal to delete lines from the records list
     *
     * @param {Array} ids the ids of the records to delete
     */
    do_delete: function (ids) {
        if (!(ids.length && confirm(_t("Do you really want to remove these records?")))) {
            return;
        }
        var self = this;
        return $.when(this.dataset.unlink(ids)).then(function () {
            _(ids).each(function (id) {
                self.records.remove(self.records.get(id));
            });
            self.configure_pager(self.dataset);
            self.compute_aggregates();
        });
    },
    /**
     * Handles the signal indicating that a new record has been selected
     *
     * @param {Array} ids selected record ids
     * @param {Array} records selected record values
     */
    do_select: function (ids, records) {
        if (!ids.length) {
            this.dataset.index = 0;
            if (this.sidebar) {
                this.sidebar.$element.hide();
            }
            this.compute_aggregates();
            return;
        }

        this.dataset.index = _(this.dataset.ids).indexOf(ids[0]);
        if (this.sidebar) {
            this.sidebar.$element.show();
        }

        this.compute_aggregates(_(records).map(function (record) {
            return {count: 1, values: record};
        }));
    },
    /**
     * Handles action button signals on a record
     *
     * @param {String} name action name
     * @param {Object} id id of the record the action should be called on
     * @param {Function} callback should be called after the action is executed, if non-null
     */
    do_button_action: function (name, id, callback) {
        this.handleButton(name, id, callback);
    },
    /**
     * Base handling of buttons, can be called when overriding do_button_action
     * in order to bypass parent overrides.
     *
     * This method should not be overridden.
     *
     * @param {String} name action name
     * @param {Object} id id of the record the action should be called on
     * @param {Function} callback should be called after the action is executed, if non-null
     */
    handleButton: function (name, id, callback) {
        var action = _.detect(this.columns, function (field) {
            return field.name === name;
        });
        if (!action) { return; }
        if ('confirm' in action && !window.confirm(action.confirm)) {
            return;
        }

        var c = new instance.web.CompoundContext();
        c.set_eval_context(_.extend({
            active_id: id,
            active_ids: [id],
            active_model: this.dataset.model
        }, this.records.get(id).toContext()));
        if (action.context) {
            c.add(action.context);
        }
        action.context = c;
        this.do_execute_action(action, this.dataset, id, callback);
    },
    /**
     * Handles the activation of a record (clicking on it)
     *
     * @param {Number} index index of the record in the dataset
     * @param {Object} id identifier of the activated record
     * @param {instance.web.DataSet} dataset dataset in which the record is available (may not be the listview's dataset in case of nested groups)
     */
    do_activate_record: function (index, id, dataset, view) {
        this.dataset.ids = dataset.ids;
        this.select_record(index, view);
    },
    /**
     * Handles signal for the addition of a new record (can be a creation,
     * can be the addition from a remote source, ...)
     *
     * The default implementation is to switch to a new record on the form view
     */
    do_add_record: function () {
        this.select_record(null);
    },
    /**
     * Handles deletion of all selected lines
     */
    do_delete_selected: function () {
        var ids = this.groups.get_selection().ids;
        if (ids.length) {
            this.do_delete(this.groups.get_selection().ids);
        } else {
            this.do_warn(_t("Warning"), _t("You must select at least one record."));
        }
    },
    /**
     * Computes the aggregates for the current list view, either on the
     * records provided or on the records of the internal
     * :js:class:`~instance.web.ListView.Group`, by calling
     * :js:func:`~instance.web.ListView.group.get_records`.
     *
     * Then displays the aggregates in the table through
     * :js:method:`~instance.web.ListView.display_aggregates`.
     *
     * @param {Array} [records]
     */
    compute_aggregates: function (records) {
        var columns = _(this.aggregate_columns).filter(function (column) {
            return column['function']; });
        if (_.isEmpty(columns)) { return; }

        if (_.isEmpty(records)) {
            records = this.groups.get_records();
        }
        records = _(records).compact();

        var count = 0, sums = {};
        _(columns).each(function (column) {
            switch (column['function']) {
                case 'max':
                    sums[column.id] = -Infinity;
                    break;
                case 'min':
                    sums[column.id] = Infinity;
                    break;
                default:
                    sums[column.id] = 0;
            }
        });
        _(records).each(function (record) {
            count += record.count || 1;
            _(columns).each(function (column) {
                var field = column.id,
                    value = record.values[field];
                switch (column['function']) {
                    case 'sum':
                        sums[field] += value;
                        break;
                    case 'avg':
                        sums[field] += record.count * value;
                        break;
                    case 'min':
                        if (sums[field] > value) {
                            sums[field] = value;
                        }
                        break;
                    case 'max':
                        if (sums[field] < value) {
                            sums[field] = value;
                        }
                        break;
                }
            });
        });

        var aggregates = {};
        _(columns).each(function (column) {
            var field = column.id;
            switch (column['function']) {
                case 'avg':
                    aggregates[field] = {value: sums[field] / count};
                    break;
                default:
                    aggregates[field] = {value: sums[field]};
            }
        });

        this.display_aggregates(aggregates);
    },
    display_aggregates: function (aggregation) {
        var self = this;
        var $footer_cells = this.$element.find('.oe_list_footer');
        _(this.aggregate_columns).each(function (column) {
            if (!column['function']) {
                return;
            }

            $footer_cells.filter(_.str.sprintf('[data-field=%s]', column.id))
                .html(instance.web.format_cell(aggregation, column, {
                    process_modifiers: false
            }));
        });
    },
    get_selected_ids: function() {
        var ids = this.groups.get_selection().ids;
        return ids;
    },
    /**
     * Adds padding columns at the start or end of all table rows (including
     * field names row)
     *
     * @param {Number} count number of columns to add
     * @param {Object} options
     * @param {"before"|"after"} [options.position="after"] insertion position for the new columns
     * @param {Object} [options.except] content row to not pad
     */
    pad_columns: function (count, options) {
        options = options || {};
        // padding for action/pager header
        var $first_header = this.$element.find('thead tr:first th');
        var colspan = $first_header.attr('colspan');
        if (colspan) {
            if (!this.previous_colspan) {
                this.previous_colspan = colspan;
            }
            $first_header.attr('colspan', parseInt(colspan, 10) + count);
        }
        // Padding for column titles, footer and data rows
        var $rows = this.$element
                .find('.oe_list_header_columns, tr:not(thead tr)')
                .not(options['except']);
        var newcols = new Array(count+1).join('<td class="oe_list_padding"></td>');
        if (options.position === 'before') {
            $rows.prepend(newcols);
        } else {
            $rows.append(newcols);
        }
    },
    /**
     * Removes all padding columns of the table
     */
    unpad_columns: function () {
        this.$element.find('.oe_list_padding').remove();
        if (this.previous_colspan) {
            this.$element
                    .find('thead tr:first th')
                    .attr('colspan', this.previous_colspan);
            this.previous_colspan = null;
        }
    },
    no_result: function () {
        this.$element.find('.oe_view_nocontent').remove();
        if (this.groups.group_by
            || !this.options.action
            || !this.options.action.help) {
            return;
        }
        this.$element.find('table:first').hide();
        this.$element.prepend(
            $('<div class="oe_view_nocontent">')
                .append($('<img>', { src: '/web/static/src/img/view_empty_arrow.png' }))
                .append($('<div>').html(this.options.action.help))
        );
    }
});
instance.web.ListView.List = instance.web.Class.extend( /** @lends instance.web.ListView.List# */{
    /**
     * List display for the ListView, handles basic DOM events and transforms
     * them in the relevant higher-level events, to which the list view (or
     * other consumers) can subscribe.
     *
     * Events on this object are registered via jQuery.
     *
     * Available events:
     *
     * `selected`
     *   Triggered when a row is selected (using check boxes), provides an
     *   array of ids of all the selected records.
     * `deleted`
     *   Triggered when deletion buttons are hit, provide an array of ids of
     *   all the records being marked for suppression.
     * `action`
     *   Triggered when an action button is clicked, provides two parameters:
     *
     *   * The name of the action to execute (as a string)
     *   * The id of the record to execute the action on
     * `row_link`
     *   Triggered when a row of the table is clicked, provides the index (in
     *   the rows array) and id of the selected record to the handle function.
     *
     * @constructs instance.web.ListView.List
     * @extends instance.web.Class
     * 
     * @param {Object} opts display options, identical to those of :js:class:`instance.web.ListView`
     */
    init: function (group, opts) {
        var self = this;
        this.group = group;
        this.view = group.view;
        this.session = this.view.session;

        this.options = opts.options;
        this.columns = opts.columns;
        this.dataset = opts.dataset;
        this.records = opts.records;

        this.record_callbacks = {
            'remove': function (event, record) {
                var $row = self.$current.children(
                    '[data-id=' + record.get('id') + ']');
                var index = $row.data('index');
                $row.remove();
                self.refresh_zebra(index);
            },
            'reset': function () { return self.on_records_reset(); },
            'change': function (event, record, attribute, value, old_value) {
                var $row;
                if (attribute === 'id') {
                    if (old_value) {
                        throw new Error("Setting 'id' attribute on existing record "
                            + JSON.stringify(record.attributes));
                    }
                    if (!_.contains(self.dataset.ids, value)) {
                        // add record to dataset if not already in (added by
                        // the form view?)
                        self.dataset.ids.splice(
                            self.records.indexOf(record), 0, value);
                    }
                    // Set id on new record
                    $row = self.$current.children('[data-id=false]');
                } else {
                    $row = self.$current.children(
                        '[data-id=' + record.get('id') + ']');
                }
                $row.replaceWith(self.render_record(record));
            },
            'add': function (ev, records, record, index) {
                var $new_row = $(self.render_record(record));

                if (index === 0) {
                    $new_row.prependTo(self.$current);
                } else {
                    var previous_record = records.at(index-1),
                        $previous_sibling = self.$current.children(
                                '[data-id=' + previous_record.get('id') + ']');
                    $new_row.insertAfter($previous_sibling);
                }

                self.refresh_zebra(index, 1);
            }
        };
        _(this.record_callbacks).each(function (callback, event) {
            this.records.bind(event, callback);
        }, this);

        this.$_element = $('<tbody>')
            .appendTo(document.body)
            .delegate('th.oe_list_record_selector', 'click', function (e) {
                e.stopPropagation();
                var selection = self.get_selection();
                $(self).trigger(
                        'selected', [selection.ids, selection.records]);
            })
            .delegate('td.oe_list_record_delete button', 'click', function (e) {
                e.stopPropagation();
                var $row = $(e.target).closest('tr');
                $(self).trigger('deleted', [[self.row_id($row)]]);
            })
            .delegate('td.oe_list_field_cell button', 'click', function (e) {
                e.stopPropagation();
                var $target = $(e.currentTarget),
                      field = $target.closest('td').data('field'),
                       $row = $target.closest('tr'),
                  record_id = self.row_id($row);

                // note: $.data converts data to number if it's composed only
                // of digits, nice when storing actual numbers, not nice when
                // storing strings composed only of digits. Force the action
                // name to be a string
                $(self).trigger('action', [field.toString(), record_id, function () {
                    return self.reload_record(self.records.get(record_id));
                }]);
            })
            .delegate('a', 'click', function (e) {
                e.stopPropagation();
            })
            .delegate('tr', 'click', function (e) {
                var row_id = self.row_id(e.currentTarget);
                if (row_id !== undefined) {
                    e.stopPropagation();
                    if (!self.dataset.select_id(row_id)) {
                        throw "Could not find id in dataset"
                    }
                    self.row_clicked(e);
                }
            });
    },
    row_clicked: function (e, view) {
        $(this).trigger(
            'row_link',
            [this.dataset.ids[this.dataset.index],
             this.dataset, view]);
    },
    render_cell: function (record, column) {
        var value;
        if(column.type === 'reference') {
            value = record.get(column.id);
            var ref_match;
            // Ensure that value is in a reference "shape", otherwise we're
            // going to loop on performing name_get after we've resolved (and
            // set) a human-readable version. m2o does not have this issue
            // because the non-human-readable is just a number, where the
            // human-readable version is a pair
            if (value && (ref_match = /([\w\.]+),(\d+)/.exec(value))) {
                // reference values are in the shape "$model,$id" (as a
                // string), we need to split and name_get this pair in order
                // to get a correctly displayable value in the field
                var model = ref_match[1],
                    id = parseInt(ref_match[2], 10);
                new instance.web.DataSet(this.view, model).name_get([id], function(names) {
                    if (!names.length) { return; }
                    record.set(column.id, names[0][1]);
                });
            }
        } else if (column.type === 'many2one') {
            value = record.get(column.id);
            // m2o values are usually name_get formatted, [Number, String]
            // pairs, but in some cases only the id is provided. In these
            // cases, we need to perform a name_get call to fetch the actual
            // displayable value
            if (typeof value === 'number' || value instanceof Number) {
                // fetch the name, set it on the record (in the right field)
                // and let the various registered events handle refreshing the
                // row
                new instance.web.DataSet(this.view, column.relation)
                        .name_get([value], function (names) {
                    if (!names.length) { return; }
                    record.set(column.id, names[0]);
                });
            }
        }
        return instance.web.format_cell(record.toForm().data, column, {
            model: this.dataset.model,
            id: record.get('id')
        });
    },
    render: function () {
        var self = this;
        if (this.$current) {
            this.$current.remove();
        }
        this.$current = this.$_element.clone(true);
        this.$current.empty().append(
            QWeb.render('ListView.rows', _.extend({
                    render_cell: function () {
                        return self.render_cell.apply(self, arguments); }
                }, this)));
        this.pad_table_to(5);
    },
    pad_table_to: function (count) {
        if (this.records.length >= count ||
                _(this.columns).any(function(column) { return column.meta; })) {
            return;
        }
        var cells = [];
        if (this.options.selectable) {
            cells.push('<th class="oe_list_record_selector"></td>');
        }
        _(this.columns).each(function(column) {
            if (column.invisible === '1') {
                return;
            }
            if (column.tag === 'button') {
                cells.push('<td class="oe_button" title="' + column.string + '">&nbsp;</td>');
            } else {
                cells.push('<td title="' + column.string + '">&nbsp;</td>');
            }
        });
        if (this.options.deletable) {
            cells.push('<td class="oe_list_record_delete"><button type="button" style="visibility: hidden"> </button></td>');
        }
        cells.unshift('<tr>');
        cells.push('</tr>');

        var row = cells.join('');
        this.$current
            .children('tr:not([data-id])').remove().end()
            .append(new Array(count - this.records.length + 1).join(row));
        this.refresh_zebra(this.records.length);
    },
    /**
     * Gets the ids of all currently selected records, if any
     * @returns {Object} object with the keys ``ids`` and ``records``, holding respectively the ids of all selected records and the records themselves.
     */
    get_selection: function () {
        var result = {ids: [], records: []};
        if (!this.options.selectable) {
            return result;
        }
        var records = this.records;
        this.$current.find('th.oe_list_record_selector input:checked')
                .closest('tr').each(function () {
            var record = records.get($(this).data('id'));
            result.ids.push(record.get('id'));
            result.records.push(record.attributes);
        });
        return result;
    },
    /**
     * Returns the identifier of the object displayed in the provided table
     * row
     *
     * @param {Object} row the selected table row
     * @returns {Number|String} the identifier of the row's object
     */
    row_id: function (row) {
        return $(row).data('id');
    },
    /**
     * Death signal, cleans up list display
     */
    on_records_reset: function () {
        _(this.record_callbacks).each(function (callback, event) {
            this.records.unbind(event, callback);
        }, this);
        if (!this.$current) { return; }
        this.$current.remove();
        this.$current = null;
        this.$_element.remove();
    },
    get_records: function () {
        return this.records.map(function (record) {
            return {count: 1, values: record.attributes};
        });
    },
    /**
     * Reloads the provided record by re-reading its content from the server.
     *
     * @param {Record} record
     * @returns {$.Deferred} promise to the finalization of the reloading
     */
    reload_record: function (record) {
        return this.view.reload_record(record);
    },
    /**
     * Renders a list record to HTML
     *
     * @param {Record} record index of the record to render in ``this.rows``
     * @returns {String} QWeb rendering of the selected record
     */
    render_record: function (record) {
        var self = this;
        var index = this.records.indexOf(record);
        return QWeb.render('ListView.row', {
            columns: this.columns,
            options: this.options,
            record: record,
            row_parity: (index % 2 === 0) ? 'even' : 'odd',
            view: this.view,
            render_cell: function () {
                return self.render_cell.apply(self, arguments); }
        });
    },
    /**
     * Fixes fixes the even/odd classes
     *
     * @param {Number} [from_index] index from which to resequence
     * @param {Number} [offset = 0] selection offset for DOM, in case there are rows to ignore in the table
     */
    refresh_zebra: function (from_index, offset) {
        offset = offset || 0;
        from_index = from_index || 0;
        var dom_offset = offset + from_index;
        var sel = dom_offset ? ':gt(' + (dom_offset - 1) + ')' : null;
        this.$current.children(sel).each(function (i, e) {
            var index = from_index + i;
            // reset record-index accelerators on rows and even/odd
            var even = index%2 === 0;
            $(e).toggleClass('even', even)
                .toggleClass('odd', !even);
        });
    }
});
instance.web.ListView.Groups = instance.web.Class.extend( /** @lends instance.web.ListView.Groups# */{
    passtrough_events: 'action deleted row_link',
    /**
     * Grouped display for the ListView. Handles basic DOM events and interacts
     * with the :js:class:`~instance.web.DataGroup` bound to it.
     *
     * Provides events similar to those of
     * :js:class:`~instance.web.ListView.List`
     *
     * @constructs instance.web.ListView.Groups
     * @extends instance.web.Class
     *
     * @param {instance.web.ListView} view
     * @param {Object} [options]
     * @param {Collection} [options.records]
     * @param {Object} [options.options]
     * @param {Array} [options.columns]
     */
    init: function (view, options) {
        options = options || {};
        this.view = view;
        this.records = options.records || view.records;
        this.options = options.options || view.options;
        this.columns = options.columns || view.columns;
        this.datagroup = null;

        this.$row = null;
        this.children = {};

        this.page = 0;

        var self = this;
        this.records.bind('reset', function () {
            return self.on_records_reset(); });
    },
    make_fragment: function () {
        return document.createDocumentFragment();
    },
    /**
     * Returns a DOM node after which a new tbody can be inserted, so that it
     * follows the provided row.
     *
     * Necessary to insert the result of a new group or list view within an
     * existing groups render, without losing track of the groups's own
     * elements
     *
     * @param {HTMLTableRowElement} row the row after which the caller wants to insert a body
     * @returns {HTMLTableSectionElement} element after which a tbody can be inserted
     */
    point_insertion: function (row) {
        var $row = $(row);
        var red_letter_tboday = $row.closest('tbody')[0];

        var $next_siblings = $row.nextAll();
        if ($next_siblings.length) {
            var $root_kanal = $('<tbody>').insertAfter(red_letter_tboday);

            $root_kanal.append($next_siblings);
            this.elements.splice(
                _.indexOf(this.elements, red_letter_tboday),
                0,
                $root_kanal[0]);
        }
        return red_letter_tboday;
    },
    make_paginator: function () {
        var self = this;
        var $prev = $('<button type="button" data-pager-action="previous">&lt;</button>')
            .click(function (e) {
                e.stopPropagation();
                self.page -= 1;

                self.$row.closest('tbody').next()
                    .replaceWith(self.render());
            });
        var $next = $('<button type="button" data-pager-action="next">&gt;</button>')
            .click(function (e) {
                e.stopPropagation();
                self.page += 1;

                self.$row.closest('tbody').next()
                    .replaceWith(self.render());
            });
        this.$row.children().last()
            .append($prev)
            .append('<span class="oe_list_pager_state"></span>')
            .append($next);
    },
    open: function (point_insertion) {
        this.render().insertAfter(point_insertion);

        var no_subgroups = _(this.datagroup.group_by).isEmpty(),
            records_terminated = !this.datagroup.context['group_by_no_leaf'];
        if (no_subgroups && records_terminated) {
            this.make_paginator();
        }
    },
    close: function () {
        this.$row.children().last().empty();
        this.records.reset();
    },
    /**
     * Prefixes ``$node`` with floated spaces in order to indent it relative
     * to its own left margin/baseline
     *
     * @param {jQuery} $node jQuery object to indent
     * @param {Number} level current nesting level, >= 1
     * @returns {jQuery} the indentation node created
     */
    indent: function ($node, level) {
        return $('<span>')
                .css({'float': 'left', 'white-space': 'pre'})
                .text(new Array(level).join('   '))
                .prependTo($node);
    },
    render_groups: function (datagroups) {
        var self = this;
        var placeholder = this.make_fragment();
        _(datagroups).each(function (group) {
            if (self.children[group.value]) {
                self.records.proxy(group.value).reset();
                delete self.children[group.value];
            }
            var child = self.children[group.value] = new (self.view.options.GroupsType)(self.view, {
                records: self.records.proxy(group.value),
                options: self.options,
                columns: self.columns
            });
            self.bind_child_events(child);
            child.datagroup = group;

            var $row = child.$row = $('<tr>');
            if (group.openable && group.length) {
                $row.click(function (e) {
                    if (!$row.data('open')) {
                        $row.data('open', true)
                            .find('span.ui-icon')
                                .removeClass('ui-icon-triangle-1-e')
                                .addClass('ui-icon-triangle-1-s');
                        child.open(self.point_insertion(e.currentTarget));
                    } else {
                        $row.removeData('open')
                            .find('span.ui-icon')
                                .removeClass('ui-icon-triangle-1-s')
                                .addClass('ui-icon-triangle-1-e');
                        child.close();
                    }
                });
            }
            placeholder.appendChild($row[0]);

            var $group_column = $('<th class="oe_list_group_name">').appendTo($row);
            // Don't fill this if group_by_no_leaf but no group_by
            if (group.grouped_on) {
                var row_data = {};
                row_data[group.grouped_on] = group;
                var group_column = _(self.columns).detect(function (column) {
                    return column.id === group.grouped_on; });
                if (! group_column) {
                    throw new Error(_.str.sprintf(
                        _t("Grouping on field '%s' is not possible because that field does not appear in the list view."),
                        group.grouped_on));
                }
                try {
                    $group_column.html(instance.web.format_cell(
                        row_data, group_column, {
                            value_if_empty: _t("Undefined"),
                            process_modifiers: false
                    }));
                } catch (e) {
                    $group_column.html(row_data[group_column.id].value);
                }
                if (group.length && group.openable) {
                    // Make openable if not terminal group & group_by_no_leaf
                    $group_column.prepend('<span class="ui-icon ui-icon-triangle-1-e" style="float: left;">');
                } else {
                    // Kinda-ugly hack: jquery-ui has no "empty" icon, so set
                    // wonky background position to ensure nothing is displayed
                    // there but the rest of the behavior is ui-icon's
                    $group_column.prepend('<span class="ui-icon" style="float: left; background-position: 150px 150px">');
                }
            }
            self.indent($group_column, group.level);
            // count column
            $('<td>').text(group.length).appendTo($row);

            if (self.options.selectable) {
                $row.append('<td>');
            }
            _(self.columns).chain()
                .filter(function (column) {return !column.invisible;})
                .each(function (column) {
                    if (column.meta) {
                        // do not do anything
                    } else if (column.id in group.aggregates) {
                        var r = {};
                        r[column.id] = {value: group.aggregates[column.id]};
                        $('<td class="oe_number">')
                            .html(instance.web.format_cell(
                                r, column, {process_modifiers: false}))
                            .appendTo($row);
                    } else {
                        $row.append('<td>');
                    }
                });
            if (self.options.deletable) {
                $row.append('<td class="oe_list_group_pagination">');
            }
        });
        return placeholder;
    },
    bind_child_events: function (child) {
        var $this = $(this),
             self = this;
        $(child).bind('selected', function (e) {
            // can have selections spanning multiple links
            var selection = self.get_selection();
            $this.trigger(e, [selection.ids, selection.records]);
        }).bind(this.passtrough_events, function (e) {
            // additional positional parameters are provided to trigger as an
            // Array, following the event type or event object, but are
            // provided to the .bind event handler as *args.
            // Convert our *args back into an Array in order to trigger them
            // on the group itself, so it can ultimately be forwarded wherever
            // it's supposed to go.
            var args = Array.prototype.slice.call(arguments, 1);
            $this.trigger.call($this, e, args);
        });
    },
    render_dataset: function (dataset) {
        var self = this,
            list = new (this.view.options.ListType)(this, {
                options: this.options,
                columns: this.columns,
                dataset: dataset,
                records: this.records
            });
        this.bind_child_events(list);

        var view = this.view,
           limit = view.limit(),
               d = new $.Deferred(),
            page = this.datagroup.openable ? this.page : view.page;

        var fields = _.pluck(_.select(this.columns, function(x) {return x.tag == "field"}), 'name');
        var options = { offset: page * limit, limit: limit, context: {bin_size: true} };
        //TODO xmo: investigate why we need to put the setTimeout
        $.async_when().then(function() {dataset.read_slice(fields, options).then(function (records) {
            // FIXME: ignominious hacks, parents (aka form view) should not send two ListView#reload_content concurrently
            if (self.records.length) {
                self.records.reset(null, {silent: true});
            }
            if (!self.datagroup.openable) {
                view.configure_pager(dataset);
            } else {
                if (dataset.size() == records.length) {
                    // only one page
                    self.$row.find('td.oe_list_group_pagination').empty();
                } else {
                    var pages = Math.ceil(dataset.size() / limit);
                    self.$row
                        .find('.oe_list_pager_state')
                            .text(_.str.sprintf(_t("%(page)d/%(page_count)d"), {
                                page: page + 1,
                                page_count: pages
                            }))
                        .end()
                        .find('button[data-pager-action=previous]')
                            .attr('disabled', page === 0)
                        .end()
                        .find('button[data-pager-action=next]')
                            .attr('disabled', page === pages - 1);
                }
            }

            self.records.add(records, {silent: true});
            list.render();
            d.resolve(list);
            if (_.isEmpty(records)) {
                view.no_result();
            }
        });});
        return d.promise();
    },
    setup_resequence_rows: function (list, dataset) {
        // drag and drop enabled if list is not sorted and there is a
        // "sequence" column in the view.
        if ((dataset.sort && dataset.sort())
            || !_(this.columns).any(function (column) {
                    return column.name === 'sequence'; })) {
            return;
        }
        // ondrop, move relevant record & fix sequences
        list.$current.sortable({
            axis: 'y',
            items: '> tr[data-id]',
            containment: 'parent',
            helper: 'clone',
            stop: function (event, ui) {
                var to_move = list.records.get(ui.item.data('id')),
                    target_id = ui.item.prev().data('id'),
                    from_index = list.records.indexOf(to_move),
                    target = list.records.get(target_id);
                if (list.records.at(from_index - 1) == target) {
                    return;
                }

                list.records.remove(to_move);
                var to = target_id ? list.records.indexOf(target) + 1 : 0;
                list.records.add(to_move, { at: to });

                // resequencing time!
                var record, index = to,
                    // if drag to 1st row (to = 0), start sequencing from 0
                    // (exclusive lower bound)
                    seq = to ? list.records.at(to - 1).get('sequence') : 0;
                while (++seq, record = list.records.at(index++)) {
                    // write are independent from one another, so we can just
                    // launch them all at the same time and we don't really
                    // give a fig about when they're done
                    // FIXME: breaks on o2ms (e.g. Accounting > Financial
                    //        Accounting > Taxes > Taxes, child tax accounts)
                    //        when synchronous (without setTimeout)
                    (function (dataset, id, seq) {
                        $.async_when().then(function () {
                            dataset.write(id, {sequence: seq});
                        });
                    }(dataset, record.get('id'), seq));
                    record.set('sequence', seq);
                }

                list.refresh_zebra();
            }
        });
    },
    render: function (post_render) {
        var self = this;
        var $element = $('<tbody>');
        this.elements = [$element[0]];

        this.datagroup.list(
            _(this.view.visible_columns).chain()
                .filter(function (column) { return column.tag === 'field' })
                .pluck('name').value(),
            function (groups) {
                $element[0].appendChild(
                    self.render_groups(groups));
                if (post_render) { post_render(); }
            }, function (dataset) {
                self.render_dataset(dataset).then(function (list) {
                    self.children[null] = list;
                    self.elements =
                        [list.$current.replaceAll($element)[0]];
                    self.setup_resequence_rows(list, dataset);
                    if (post_render) { post_render(); }
                });
            });
        return $element;
    },
    /**
     * Returns the ids of all selected records for this group, and the records
     * themselves
     */
    get_selection: function () {
        var ids = [], records = [];

        _(this.children)
            .each(function (child) {
                var selection = child.get_selection();
                ids.push.apply(ids, selection.ids);
                records.push.apply(records, selection.records);
            });

        return {ids: ids, records: records};
    },
    on_records_reset: function () {
        this.children = {};
        $(this.elements).remove();
    },
    get_records: function () {
        if (_(this.children).isEmpty()) {
            if (!this.datagroup.length) {
                return;
            }
            return {
                count: this.datagroup.length,
                values: this.datagroup.aggregates
            }
        }
        return _(this.children).chain()
            .map(function (child) {
                return child.get_records();
            }).flatten().value();
    }
});

/**
 * @mixin Events
 */
var Events = /** @lends Events# */{
    /**
     * @param {String} event event to listen to on the current object, null for all events
     * @param {Function} handler event handler to bind to the relevant event
     * @returns this
     */
    bind: function (event, handler) {
        var calls = this['_callbacks'] || (this._callbacks = {});

        if (event in calls) {
            calls[event].push(handler);
        } else {
            calls[event] = [handler];
        }
        return this;
    },
    /**
     * @param {String} event event to unbind on the current object
     * @param {function} [handler] specific event handler to remove (otherwise unbind all handlers for the event)
     * @returns this
     */
    unbind: function (event, handler) {
        var calls = this._callbacks || {};
        if (!(event in calls)) { return this; }
        if (!handler) {
            delete calls[event];
        } else {
            var handlers = calls[event];
            handlers.splice(
                _(handlers).indexOf(handler),
                1);
        }
        return this;
    },
    /**
     * @param {String} event
     * @returns this
     */
    trigger: function (event) {
        var calls;
        if (!(calls = this._callbacks)) { return this; }
        var callbacks = (calls[event] || []).concat(calls[null] || []);
        for(var i=0, length=callbacks.length; i<length; ++i) {
            callbacks[i].apply(this, arguments);
        }
        return this;
    }
};
var Record = instance.web.Class.extend(/** @lends Record# */{
    /**
     * @constructs Record
     * @extends instance.web.Class
     * 
     * @mixes Events
     * @param {Object} [data]
     */
    init: function (data) {
        this.attributes = data || {};
    },
    /**
     * @param {String} key
     * @returns {Object}
     */
    get: function (key) {
        return this.attributes[key];
    },
    /**
     * @param key
     * @param value
     * @param {Object} [options]
     * @param {Boolean} [options.silent=false]
     * @returns {Record}
     */
    set: function (key, value, options) {
        options = options || {};
        var old_value = this.attributes[key];
        if (old_value === value) {
            return this;
        }
        this.attributes[key] = value;
        if (!options.silent) {
            this.trigger('change:' + key, this, value, old_value);
            this.trigger('change', this, key, value, old_value);
        }
        return this;
    },
    /**
     * Converts the current record to the format expected by form views:
     *
     * .. code-block:: javascript
     *
     *    data: {
     *         $fieldname: {
     *             value: $value
     *         }
     *     }
     *
     *
     * @returns {Object} record displayable in a form view
     */
    toForm: function () {
        var form_data = {}, attrs = this.attributes;
        for(var k in attrs) {
            form_data[k] = {value: attrs[k]};
        }

        return {data: form_data};
    },
    /**
     * Converts the current record to a format expected by context evaluations
     * (identical to record.attributes, except m2o fields are their integer
     * value rather than a pair)
     */
    toContext: function () {
        var output = {}, attrs = this.attributes;
        for(var k in attrs) {
            var val = attrs[k];
            if (typeof val !== 'object') {
                output[k] = val;
            } else if (val instanceof Array) {
                output[k] = val[0];
            } else {
                throw new Error("Can't convert value " + val + " to context");
            }
        }
        return output;
    }
});
Record.include(Events);
var Collection = instance.web.Class.extend(/** @lends Collection# */{
    /**
     * Smarter collections, with events, very strongly inspired by Backbone's.
     *
     * Using a "dumb" array of records makes synchronization between the
     * various serious 
     *
     * @constructs Collection
     * @extends instance.web.Class
     * 
     * @mixes Events
     * @param {Array} [records] records to initialize the collection with
     * @param {Object} [options]
     */
    init: function (records, options) {
        options = options || {};
        _.bindAll(this, '_onRecordEvent');
        this.length = 0;
        this.records = [];
        this._byId = {};
        this._proxies = {};
        this._key = options.key;
        this._parent = options.parent;

        if (records) {
            this.add(records);
        }
    },
    /**
     * @param {Object|Array} record
     * @param {Object} [options]
     * @param {Number} [options.at]
     * @param {Boolean} [options.silent=false]
     * @returns this
     */
    add: function (record, options) {
        options = options || {};
        var records = record instanceof Array ? record : [record];

        for(var i=0, length=records.length; i<length; ++i) {
            var instance_ = (records[i] instanceof Record) ? records[i] : new Record(records[i]);
            instance_.bind(null, this._onRecordEvent);
            this._byId[instance_.get('id')] = instance_;
            if (options.at == undefined) {
                this.records.push(instance_);
                if (!options.silent) {
                    this.trigger('add', this, instance_, this.records.length-1);
                }
            } else {
                var insertion_index = options.at + i;
                this.records.splice(insertion_index, 0, instance_);
                if (!options.silent) {
                    this.trigger('add', this, instance_, insertion_index);
                }
            }
            this.length++;
        }
        return this;
    },

    /**
     * Get a record by its index in the collection, can also take a group if
     * the collection is not degenerate
     *
     * @param {Number} index
     * @param {String} [group]
     * @returns {Record|undefined}
     */
    at: function (index, group) {
        if (group) {
            var groups = group.split('.');
            return this._proxies[groups[0]].at(index, groups.join('.'));
        }
        return this.records[index];
    },
    /**
     * Get a record by its database id
     *
     * @param {Number} id
     * @returns {Record|undefined}
     */
    get: function (id) {
        if (!_(this._proxies).isEmpty()) {
            var record = null;
            _(this._proxies).detect(function (proxy) {
                return record = proxy.get(id);
            });
            return record;
        }
        return this._byId[id];
    },
    /**
     * Builds a proxy (insert/retrieve) to a subtree of the collection, by
     * the subtree's group
     *
     * @param {String} section group path section
     * @returns {Collection}
     */
    proxy: function (section) {
        return this._proxies[section] = new Collection(null, {
            parent: this,
            key: section
        }).bind(null, this._onRecordEvent);
    },
    /**
     * @param {Array} [records]
     * @returns this
     */
    reset: function (records, options) {
        options = options || {};
        _(this._proxies).each(function (proxy) {
            proxy.reset();
        });
        this._proxies = {};
        _(this.records).invoke('unbind', null, this._onRecordEvent);
        this.length = 0;
        this.records = [];
        this._byId = {};
        if (records) {
            this.add(records);
        }
        if (!options.silent) {
            this.trigger('reset', this);
        }
        return this;
    },
    /**
     * Removes the provided record from the collection
     *
     * @param {Record} record
     * @returns this
     */
    remove: function (record) {
        var index = this.indexOf(record);
        if (index === -1) {
            _(this._proxies).each(function (proxy) {
                proxy.remove(record);
            });
            return this;
        }

        record.unbind(null, this._onRecordEvent);
        this.records.splice(index, 1);
        delete this._byId[record.get('id')];
        this.length--;
        this.trigger('remove', record, this);
        return this;
    },

    _onRecordEvent: function (event) {
        switch(event) {
        // don't propagate reset events
        case 'reset': return;
        case 'change:id':
            var record = arguments[1];
            var new_value = arguments[2];
            var old_value = arguments[3];
            // [change:id, record, new_value, old_value]
            if (this._byId[old_value] === record) {
                delete this._byId[old_value];
                this._byId[new_value] = record;
            }
            break;
        }
        this.trigger.apply(this, arguments);
    },

    // underscore-type methods
    find: function (callback) {
        var record;
        for(var section in this._proxies) {
            if (!this._proxies.hasOwnProperty(section)) {
                continue
            }
            if ((record = this._proxies[section].find(callback))) {
                return record;
            }
        }
        for(var i=0; i<this.length; ++i) {
            record = this.records[i];
            if (callback(record)) {
                return record;
            }
        }
    },
    each: function (callback) {
        for(var section in this._proxies) {
            if (this._proxies.hasOwnProperty(section)) {
                this._proxies[section].each(callback);
            }
        }
        for(var i=0; i<this.length; ++i) {
            callback(this.records[i]);
        }
    },
    map: function (callback) {
        var results = [];
        this.each(function (record) {
            results.push(callback(record));
        });
        return results;
    },
    pluck: function (fieldname) {
        return this.map(function (record) {
            return record.get(fieldname);
        });
    },
    indexOf: function (record) {
        return _(this.records).indexOf(record);
    },
    succ: function (record, options) {
        options = options || {wraparound: false};
        var result;
        for(var section in this._proxies) {
            if (!this._proxies.hasOwnProperty(section)) {
                continue;
            }
            if ((result = this._proxies[section].succ(record, options))) {
                return result;
            }
        }
        var index = this.indexOf(record);
        if (index === -1) { return null; }
        var next_index = index + 1;
        if (options.wraparound && (next_index === this.length)) {
            return this.at(0);
        }
        return this.at(next_index);
    },
    pred: function (record, options) {
        options = options || {wraparound: false};

        var result;
        for (var section in this._proxies) {
            if (!this._proxies.hasOwnProperty(section)) {
                continue;
            }
            if ((result = this._proxies[section].pred(record, options))) {
                return result;
            }
        }

        var index = this.indexOf(record);
        if (index === -1) { return null; }
        var next_index = index - 1;
        if (options.wraparound && (next_index === -1)) {
            return this.at(this.length - 1);
        }
        return this.at(next_index);
    }
});
Collection.include(Events);
instance.web.list = {
    Events: Events,
    Record: Record,
    Collection: Collection
}
};
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
