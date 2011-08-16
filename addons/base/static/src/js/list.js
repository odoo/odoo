openerp.base.list = function (openerp) {
openerp.base.views.add('list', 'openerp.base.ListView');
openerp.base.ListView = openerp.base.View.extend( /** @lends openerp.base.ListView# */ {
    defaults: {
        // records can be selected one by one
        'selectable': true,
        // list rows can be deleted
        'deletable': true,
        // whether the column headers should be displayed
        'header': true,
        // display addition button, with that label
        'addable': "New",
        // whether the list view can be sorted, note that once a view has been
        // sorted it can not be reordered anymore
        'sortable': true,
        // whether the view rows can be reordered (via vertical drag & drop)
        'reorderable': true
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
     * @constructs
     * @param parent parent object
     * @param element_id the id of the DOM elements this view should link itself to
     * @param {openerp.base.DataSet} dataset the dataset the view should work with
     * @param {String} view_id the listview's identifier, if any
     * @param {Object} options A set of options used to configure the view
     * @param {Boolean} [options.selectable=true] determines whether view rows are selectable (e.g. via a checkbox)
     * @param {Boolean} [options.header=true] should the list's header be displayed
     * @param {Boolean} [options.deletable=true] are the list rows deletable
     * @param {void|String} [options.addable="New"] should the new-record button be displayed, and what should its label be. Use ``null`` to hide the button.
     * @param {Boolean} [options.sortable=true] is it possible to sort the table by clicking on column headers
     * @param {Boolean} [options.reorderable=true] is it possible to reorder list rows
     *
     * @borrows openerp.base.ActionExecutor#execute_action as #execute_action
     */
    init: function(parent, element_id, dataset, view_id, options) {
        this._super(parent, element_id);
        this.set_default_options(_.extend({}, this.defaults, options || {}));
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;

        this.columns = [];

        this.set_groups(new openerp.base.ListView.Groups(this));

        if (this.dataset instanceof openerp.base.DataSetStatic) {
            this.groups.datagroup = new openerp.base.StaticDataGroup(this.dataset);
        }

        this.page = 0;
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
                        || (this.widget_parent.action || {}).limit
                        || null);
        }
        return this._limit;
    },
    /**
     * Set a custom Group construct as the root of the List View.
     *
     * @param {openerp.base.ListView.Groups} groups
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
            'row_link': function (e, id, dataset) {
                self.do_activate_record(dataset.index, id, dataset);
            }
        });
    },
    /**
     * View startup method, the default behavior is to set the ``oe-listview``
     * class on its root element and to perform an RPC load call.
     *
     * @returns {$.Deferred} loading promise
     */
    start: function() {
        this.$element.addClass('oe-listview');
        return this.reload_view();
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
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);
        this.name = "" + this.fields_view.arch.attrs.string;

        this.setup_columns(this.fields_view.fields, grouped);

        this.$element.html(QWeb.render("ListView", this));

        // Head hook
        this.$element.find('.oe-list-add')
                .click(this.do_add_record)
                .attr('disabled', grouped && this.options.editable);
        this.$element.find('.oe-list-delete')
                .attr('disabled', true)
                .click(this.do_delete_selected);
        this.$element.find('thead').delegate('th.oe-sortable[data-id]', 'click', function (e) {
            e.stopPropagation();

            var $this = $(this);
            self.dataset.sort($this.data('id'));
            if ($this.find('span').length) {
                $this.find('span').toggleClass(
                    'ui-icon-triangle-1-s ui-icon-triangle-1-n');
            } else {
                $this.append('<span class="ui-icon ui-icon-triangle-1-s">')
                     .siblings('.oe-sortable').find('span').remove();
            }

            self.reload_content();
        });

        this.$element.find('.oe-list-pager')
            .delegate('button', 'click', function () {
                var $this = $(this);
                switch ($this.data('pager-action')) {
                    case 'first':
                        self.page = 0; break;
                    case 'last':
                        self.page = Math.floor(
                            self.dataset.ids.length / self.limit());
                        break;
                    case 'next':
                        self.page += 1; break;
                    case 'previous':
                        self.page -= 1; break;
                }
                self.reload_content();
            }).find('.oe-pager-state')
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
                                '<option value="NaN">Unlimited</option>')
                        .change(function () {
                            var val = parseInt($select.val(), 10);
                            self._limit = (isNaN(val) ? null : val);
                            self.page = 0;
                            self.reload_content();
                        })
                        .val(self._limit || 'NaN');
                });
        if (!this.sidebar && this.options.sidebar && this.options.sidebar_id) {
            this.sidebar = new openerp.base.Sidebar(this, this.options.sidebar_id);
            this.sidebar.start();
            this.sidebar.add_toolbar(data.fields_view.toolbar);
            this.set_common_sidebar_sections(this.sidebar);
        }
    },
    /**
     * Configures the ListView pager based on the provided dataset's information
     *
     * Horrifying side-effect: sets the dataset's data on this.dataset?
     *
     * @param {openerp.base.DataSet} dataset
     */
    configure_pager: function (dataset) {
        this.dataset.ids = dataset.ids;

        var limit = this.limit(),
            total = dataset.ids.length,
            first = (this.page * limit),
            last;
        if (!limit || (total - first) < limit) {
            last = total;
        } else {
            last = first + limit;
        }
        this.$element.find('span.oe-pager-state').empty().text(_.sprintf(
            "[%d to %d] of %d", first + 1, last, total));

        this.$element
            .find('button[data-pager-action=first], button[data-pager-action=previous]')
                .attr('disabled', this.page === 0)
            .end()
            .find('button[data-pager-action=last], button[data-pager-action=next]')
                .attr('disabled', last === total);
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
        var domain_computer = openerp.base.form.compute_domain;

        var noop = function () { return {}; };
        var field_to_column = function (field) {
            var name = field.attrs.name;
            var column = _.extend({id: name, tag: field.tag},
                    field.attrs, fields[name]);
            // modifiers computer
            if (column.modifiers) {
                var modifiers = JSON.parse(column.modifiers);
                column.modifiers_for = function (fields) {
                    if (!modifiers.invisible) {
                        return {};
                    }
                    return {
                        'invisible': domain_computer(modifiers.invisible, fields)
                    };
                };
                if (modifiers['tree_invisible']) {
                    column.invisible = '1';
                }
            } else {
                column.modifiers_for = noop;
            }
            return column;
        };

        this.columns.splice(0, this.columns.length);
        this.columns.push.apply(
                this.columns,
                _(this.fields_view.arch.children).map(field_to_column));
        if (grouped) {
            this.columns.unshift({
                id: '_group', tag: '', string: "Group", meta: true,
                modifiers_for: function () { return {}; }
            }, {
                id: '_count', tag: '', string: '#', meta: true,
                modifiers_for: function () { return {}; }
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
     * :js:func:`~openerp.base.ViewManager.on_mode_switch`), using the
     * provided record index (within the current list view's dataset).
     *
     * If the index is null, ``switch_to_record`` asks for the creation of a
     * new record.
     *
     * @param {Number|void} index the record index (in the current dataset) to switch to
     * @param {String} [view="form"] the view type to switch to
     */
    select_record:function (index, view) {
        view = view || 'form';
        this.dataset.index = index;
        _.delay(_.bind(function () {
            this.do_switch_view(view);
        }, this));
    },
    do_show: function () {
        this.$element.show();
        if (this.sidebar) {
            this.sidebar.$element.show();
        }
        if (this.hidden) {
            this.$element.find('.oe-listview-content').append(
                this.groups.apoptosis().render());
            this.hidden = false;
        }
    },
    do_hide: function () {
        this.$element.hide();
        if (this.sidebar) {
            this.sidebar.$element.hide();
        }
        this.hidden = true;
    },
    /**
     * Reloads the list view based on the current settings (dataset & al)
     *
     * @param {Boolean} [grouped] Should the list be displayed grouped
     * @param {Object} [context] context to send the server while loading the view
     */
    reload_view: function (grouped, context) {
        var self = this;
        var callback = function (field_view_get) {
            self.on_loaded(field_view_get, grouped);
        };
        if (this.embedded_view) {
            return $.Deferred().then(callback).resolve({fields_view: this.embedded_view});
        } else {
            return this.rpc('/base/listview/load', {
                model: this.model,
                view_id: this.view_id,
                context: this.dataset.get_context(context),
                toolbar: this.options.sidebar
            }, callback);
        }
    },
    /**
     * re-renders the content of the list view
     */
    reload_content: function () {
        this.$element.find('.oe-listview-content').append(
            this.groups.apoptosis().render(
                $.proxy(this, 'compute_aggregates')));
    },
    /**
     * Event handler for a search, asks for the computation/folding of domains
     * and contexts (and group-by), then reloads the view's content.
     *
     * @param {Array} domains a sequence of literal and non-literal domains
     * @param {Array} contexts a sequence of literal and non-literal contexts
     * @param {Array} groupbys a sequence of literal and non-literal group-by contexts
     * @returns {$.Deferred} fold request evaluation promise
     */
    do_search: function (domains, contexts, groupbys) {
        return this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: groupbys
        }, $.proxy(this, 'do_actual_search'));
    },
    /**
     * Handler for the result of eval_domain_and_context, actually perform the
     * searching
     *
     * @param {Object} results results of evaluating domain and process for a search
     */
    do_actual_search: function (results) {
        this.groups.datagroup = new openerp.base.DataGroup(
            this, this.model,
            this.dataset.get_domain(results.domain),
            this.dataset.get_context(results.context),
            results.group_by);
        this.groups.datagroup.sort = this.dataset._sort;

        if (_.isEmpty(results.group_by) && !results.context['group_by_no_leaf']) {
            results.group_by = null;
        }

        this.reload_view(!!results.group_by, results.context).then(
            $.proxy(this, 'reload_content'));
    },
    /**
     * Handles the signal to delete lines from the records list
     *
     * @param {Array} ids the ids of the records to delete
     */
    do_delete: function (ids) {
        if (!ids.length) {
            return;
        }
        var self = this;
        return $.when(this.dataset.unlink(ids)).then(function () {
            self.groups.drop_records(ids);
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
        this.$element.find('.oe-list-delete')
            .attr('disabled', !ids.length);

        if (!records.length) {
            this.compute_aggregates();
            return;
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
        var   self = this,
            action = _.detect(this.columns, function (field) {
            return field.name === name;
        });
        if (!action) { return; }
        this.execute_action(action, this.dataset, id, function () {
            $.when(callback.apply(this, arguments).then(function () {
                self.compute_aggregates();
            }));
        });
    },
    /**
     * Handles the activation of a record (clicking on it)
     *
     * @param {Number} index index of the record in the dataset
     * @param {Object} id identifier of the activated record
     * @param {openerp.base.DataSet} dataset dataset in which the record is available (may not be the listview's dataset in case of nested groups)
     */
    do_activate_record: function (index, id, dataset) {
        var self = this;
        this.dataset.read_slice({
                context: dataset.get_context(),
                domain: dataset.get_domain()
            }, function () {
                self.select_record(index);
        });
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
        this.do_delete(this.groups.get_selection().ids);
    },
    /**
     * Computes the aggregates for the current list view, either on the
     * records provided or on the records of the internal
     * :js:class:`~openerp.base.ListView.Group`, by calling
     * :js:func:`~openerp.base.ListView.group.get_records`.
     *
     * Then displays the aggregates in the table through
     * :js:method:`~openerp.base.ListView.display_aggregates`.
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
        var $footer_cells = this.$element.find('.oe-list-footer');
        _(this.aggregate_columns).each(function (column) {
            if (!column['function']) {
                return;
            }

            $footer_cells.filter(_.sprintf('[data-field=%s]', column.id))
                .html(openerp.base.format_cell(aggregation, column));
        });
    }
    // TODO: implement reorder (drag and drop rows)
});
openerp.base.ListView.List = openerp.base.Class.extend( /** @lends openerp.base.ListView.List# */{
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
     * @constructs
     * @param {Object} opts display options, identical to those of :js:class:`openerp.base.ListView`
     */
    init: function (group, opts) {
        var self = this;
        this.group = group;
        this.view = group.view;
        this.session = this.view.session;

        this.options = opts.options;
        this.columns = opts.columns;
        this.dataset = opts.dataset;
        this.rows = opts.rows;

        this.$_element = $('<tbody class="ui-widget-content">')
            .appendTo(document.body)
            .delegate('th.oe-record-selector', 'click', function (e) {
                e.stopPropagation();
                var selection = self.get_selection();
                $(self).trigger(
                        'selected', [selection.ids, selection.records]);
            })
            .delegate('td.oe-record-delete button', 'click', function (e) {
                e.stopPropagation();
                var $row = $(e.target).closest('tr');
                $(self).trigger('deleted', [[self.row_id($row)]]);
            })
            .delegate('td.oe-field-cell button', 'click', function (e) {
                e.stopPropagation();
                var $target = $(e.currentTarget),
                      field = $target.closest('td').data('field'),
                       $row = $target.closest('tr'),
                  record_id = self.row_id($row),
                      index = self.row_position($row);

                $(self).trigger('action', [field, record_id, function () {
                    return self.reload_record(index, true);
                }]);
            })
            .delegate('tr', 'click', function (e) {
                e.stopPropagation();
                self.dataset.index = self.row_position(e.currentTarget);
                self.row_clicked(e);
            });
    },
    row_clicked: function () {
        $(this).trigger(
            'row_link',
            [this.rows[this.dataset.index].data.id.value,
             this.dataset]);
    },
    render: function () {
        if (this.$current) {
            this.$current.remove();
        }
        this.$current = this.$_element.clone(true);
        this.$current.empty().append(
            QWeb.render('ListView.rows', _.extend({
                render_cell: openerp.base.format_cell}, this)));
    },
    /**
     * Gets the ids of all currently selected records, if any
     * @returns {Object} object with the keys ``ids`` and ``records``, holding respectively the ids of all selected records and the records themselves.
     */
    get_selection: function () {
        if (!this.options.selectable) {
            return [];
        }
        var rows = this.rows;
        var result = {ids: [], records: []};
        this.$current.find('th.oe-record-selector input:checked')
                .closest('tr').each(function () {
            var record = {};
            _(rows[$(this).data('index')].data).each(function (obj, key) {
                record[key] = obj.value;
            });
            result.ids.push(record.id);
            result.records.push(record);
        });
        return result;
    },
    /**
     * Returns the index of the row in the list of rows.
     *
     * @param {Object} row the selected row
     * @returns {Number} the position of the row in this.rows
     */
    row_position: function (row) {
        return $(row).data('index');
    },
    /**
     * Returns the identifier of the object displayed in the provided table
     * row
     *
     * @param {Object} row the selected table row
     * @returns {Number|String} the identifier of the row's object
     */
    row_id: function (row) {
        return this.rows[this.row_position(row)].data.id.value;
    },
    /**
     * Death signal, cleans up list
     */
    apoptosis: function () {
        if (!this.$current) { return; }
        this.$current.remove();
        this.$current = null;
        this.$_element.remove();
    },
    get_records: function () {
        return _(this.rows).map(function (row) {
            var record = {};
            _(row.data).each(function (obj, key) {
                record[key] = obj.value;
            });
            return {count: 1, values: record};
        });
    },
    /**
     * Transforms a record from what is returned by a dataset read (a simple
     * mapping of ``$fieldname: $value``) to the format expected by list rows
     * and form views:
     *
     *    data: {
     *         $fieldname: {
     *             value: $value
     *         }
     *     }
     *
     * This format allows for the insertion of a bunch of metadata (names,
     * colors, etc...)
     *
     * @param {Object} record original record, in dataset format
     * @returns {Object} record displayable in a form or list view
     */
    transform_record: function (record) {
        // TODO: colors handling
        var form_data = {},
          form_record = {data: form_data};

        _(record).each(function (value, key) {
            form_data[key] = {value: value};
        });

        return form_record;
    },
    /**
     * Reloads the record at index ``row_index`` in the list's rows.
     *
     * By default, simply re-renders the record. If the ``fetch`` parameter is
     * provided and ``true``, will first fetch the record anew.
     *
     * @param {Number} record_index index of the record to reload
     * @param {Boolean} fetch fetches the record from remote before reloading it
     */
    reload_record: function (record_index, fetch) {
        var self = this;
        var read_p = null;
        if (fetch) {
            // save index to restore it later, if already set
            var old_index = this.dataset.index;
            this.dataset.index = record_index;
            read_p = this.dataset.read_index(
                _.pluck(_(this.columns).filter(function (r) {return r.tag === 'field';}), 'name'),
                function (record) {
                    var form_record = self.transform_record(record);
                    self.rows.splice(record_index, 1, form_record);
                    self.dataset.index = old_index;
                }
            )
        }

        return $.when(read_p).then(function () {
            self.$current.children().eq(record_index)
                .replaceWith(self.render_record(record_index)); });
    },
    /**
     * Renders a list record to HTML
     *
     * @param {Number} record_index index of the record to render in ``this.rows``
     * @returns {String} QWeb rendering of the selected record
     */
    render_record: function (record_index) {
        return QWeb.render('ListView.row', {
            columns: this.columns,
            options: this.options,
            row: this.rows[record_index],
            row_parity: (record_index % 2 === 0) ? 'even' : 'odd',
            row_index: record_index,
            render_cell: openerp.base.format_cell
        });
    },
    /**
     * Stops displaying the records matching the provided ids.
     *
     * @param {Array} ids identifiers of the records to remove
     */
    drop_records: function (ids) {
        var self = this;
        _(this.rows).chain()
              .map(function (record, index) {
                return {index: index, id: record.data.id.value};
            }).filter(function (record) {
                return _(ids).contains(record.id);
            }).reverse()
              .each(function (record) {
                self.$current.find('tr:eq(' + record.index + ')').remove();
                self.rows.splice(record.index, 1);
            })
    }
    // drag and drop
});
openerp.base.ListView.Groups = openerp.base.Class.extend( /** @lends openerp.base.ListView.Groups# */{
    passtrough_events: 'action deleted row_link',
    /**
     * Grouped display for the ListView. Handles basic DOM events and interacts
     * with the :js:class:`~openerp.base.DataGroup` bound to it.
     *
     * Provides events similar to those of
     * :js:class:`~openerp.base.ListView.List`
     */
    init: function (view) {
        this.view = view;
        this.options = view.options;
        this.columns = view.columns;
        this.datagroup = null;

        this.$row = null;
        this.children = {};

        this.page = 0;
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
            .append('<span class="oe-pager-state"></span>')
            .append($next);
    },
    open: function (point_insertion) {
        this.render().insertAfter(point_insertion);
        this.make_paginator();
    },
    close: function () {
        this.$row.children().last().empty();
        this.apoptosis();
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
                self.children[group.value].apoptosis();
                delete self.children[group.value];
            }
            var child = self.children[group.value] = new openerp.base.ListView.Groups(self.view, {
                options: self.options,
                columns: self.columns
            });
            self.bind_child_events(child);
            child.datagroup = group;

            var $row = child.$row = $('<tr>');
            if (group.openable) {
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

            var $group_column = $('<th class="oe-group-name">').appendTo($row);
            // Don't fill this if group_by_no_leaf but no group_by
            if (group.grouped_on) {
                var row_data = {};
                row_data[group.grouped_on] = group;
                var group_column = _(self.columns).detect(function (column) {
                    return column.id === group.grouped_on; });
                $group_column.html(openerp.base.format_cell(
                    row_data, group_column, "Undefined"
                ));
                if (group.openable) {
                    // Make openable if not terminal group & group_by_no_leaf
                    $group_column
                        .prepend('<span class="ui-icon ui-icon-triangle-1-e" style="float: left;">');
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
                        var value = group.aggregates[column.id];
                        var format;
                        if (column.type === 'integer') {
                            format = "%.0f";
                        } else if (column.type === 'float') {
                            format = "%.2f";
                        }
                        $('<td>')
                            .text(_.sprintf(format, value))
                            .appendTo($row);
                    } else {
                        $row.append('<td>');
                    }
                });
            if (self.options.deletable) {
                $row.append('<td class="oe-group-pagination">');
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
        var rows = [],
            self = this,
            list = new openerp.base.ListView.List(this, {
                options: this.options,
                columns: this.columns,
                dataset: dataset,
                rows: rows
            });
        this.bind_child_events(list);

        var view = this.view,
           limit = view.limit(),
               d = new $.Deferred(),
            page = this.datagroup.openable ? this.page : view.page;

        dataset.read_slice({
                fields: _.pluck(_.select(this.columns, function(x) {return x.tag == "field"}), 'name'),
                offset: page * limit,
                limit: limit
            }, function (records) {
                if (!self.datagroup.openable) {
                    view.configure_pager(dataset);
                } else {
                    var pages = Math.ceil(dataset.ids.length / limit);
                    self.$row
                        .find('.oe-pager-state')
                            .text(_.sprintf('%d/%d', page + 1, pages))
                        .end()
                        .find('button[data-pager-action=previous]')
                            .attr('disabled', page === 0)
                        .end()
                        .find('button[data-pager-action=next]')
                            .attr('disabled', page === pages - 1);
                }

                var form_records = _(records).map(
                    $.proxy(list, 'transform_record'));

                rows.splice(0, rows.length);
                rows.push.apply(rows, form_records);
                list.render();
                d.resolve(list);
            });
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
            stop: function (event, ui) {
                var from = ui.item.data('index'),
                      to = ui.item.prev().data('index') || 0;
                if (from === to) { return; }
                list.rows.splice(to, 0, list.rows.splice(from, 1)[0]);

                ui.item.parent().children().each(function (i, e) {
                    // reset record-index accelerators on rows and even/odd
                    var even = i%2 === 0;
                    $(e).data('index', i)
                        .toggleClass('even', even)
                        .toggleClass('odd', !even);
                });

                // resequencing time!
                var data, index = to,
                    // if drag to 1st row (to = 0), start sequencing from 0
                    // (exclusive lower bound)
                    seq = to ? list.rows[to - 1].data.sequence.value : 0;
                while (++seq, list.rows[index]) {
                    data = list.rows[index].data;
                    data.sequence.value = seq;
                    // write are independent from one another, so we can just
                    // launch them all at the same time and we don't really
                    // give a fig about when they're done
                    dataset.write(data.id.value, {sequence: seq});
                    list.reload_record(index++);
                }
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
    apoptosis: function () {
        _(this.children).each(function (child) {
            child.apoptosis();
        });
        this.children = {};
        $(this.elements).remove();
        return this;
    },
    get_records: function () {
        if (_(this.children).isEmpty()) {
            return {
                count: this.datagroup.length,
                values: this.datagroup.aggregates
            }
        }
        return _(this.children).chain()
            .map(function (child) {
                return child.get_records();
            }).flatten().value();
    },
    /**
     * Stops displaying the records with the linked ids, assumes these records
     * were deleted from the DB.
     *
     * This is the up-signal from the `deleted` event on groups and lists.
     *
     * @param {Array} ids list of identifier of the records to remove.
     */
    drop_records: function (ids) {
        _.each(this.children, function (child) {
            child.drop_records(ids);
        });
    }
});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:

