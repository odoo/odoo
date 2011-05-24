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
     * @param view_manager
     * @param session An OpenERP session object
     * @param element_id the id of the DOM elements this view should link itself to
     * @param {openerp.base.DataSet} dataset the dataset the view should work with
     * @param {String} view_id the listview's identifier, if any
     * @param {Object} options A set of options used to configure the view
     * @param {Boolean} [options.selectable=true] determines whether view rows are selectable (e.g. via a checkbox)
     * @param {Boolean} [options.header=true] should the list's header be displayed
     * @param {Boolean} [options.deletable=true] are the list rows deletable
     * @param {null|String} [options.addable="New"] should the new-record button be displayed, and what should its label be. Use ``null`` to hide the button.
     * @param {Boolean} [options.sortable=true] is it possible to sort the table by clicking on column headers
     * @param {Boolean} [options.reorderable=true] is it possible to reorder list rows
     *
     * @borrows openerp.base.ActionExecutor#execute_action as #execute_action
     */
    init: function(view_manager, session, element_id, dataset, view_id, options) {
        var self = this;
        this._super(session, element_id);
        this.view_manager = view_manager || new openerp.base.NullViewManager();
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;

        this.columns = [];
        this.rows = [];

        this.options = _.extend({}, this.defaults, options || {});
        this.flags =  this.view_manager.action.flags;

        this.list = new openerp.base.ListView.List({
            options: this.options,
            columns: this.columns,
            rows: this.rows
        });
        this.groups = new openerp.base.ListView.Groups({
            options: this.options,
            columns: this.columns
        });
        $([this.list, this.groups]).bind({
            'selected': function (e, selection) {
                self.$element.find('#oe-list-delete')
                    .toggle(!!selection.length);
            },
            'deleted': function (e, ids) {
                self.do_delete(ids);
            },
            'action': function (e, action_name, id) {
                var action = _.detect(self.columns, function (field) {
                    return field.name === action_name;
                });
                if (!action) { return; }
                // TODO: not supposed to reload everything, I think
                self.execute_action(
                    action, self.dataset, self.session.action_manager,
                    id, self.do_reload);
            },
            'row_link': function (e, index) {
                self.select_record(index);
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
        return this.rpc("/base/listview/load", {
            model: this.model,
            view_id: this.view_id,
            toolbar: !!this.flags.sidebar
        }, this.on_loaded);
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
     */
    on_loaded: function(data) {
        var self = this;
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);
        this.name = "" + this.fields_view.arch.attrs.string;

        var fields = this.fields_view.fields;
        var domain_computer = openerp.base.form.compute_domain;

        this.columns.splice(0, this.columns.length);
        this.columns.push.apply(this.columns, _(this.fields_view.arch.children).chain()
            .map(function (field) {
                var name = field.attrs.name;
                var column = _.extend({id: name, tag: field.tag},
                                      field.attrs, fields[name]);
                // attrs computer
                if (column.attrs) {
                    var attrs = eval('(' + column.attrs + ')');
                    column.attrs_for = function (fields) {
                        var result = {};
                        for (var attr in attrs) {
                            result[attr] = domain_computer(attrs[attr], fields);
                        }
                        return result;
                    };
                } else {
                    column.attrs_for = function () { return {}; };
                }
                return column;
            }).value());

        this.visible_columns = _.filter(this.columns, function (column) {
            return column.invisible !== '1';
        });

        if (!this.fields_view.sorted) { this.fields_view.sorted = {}; }

        this.$element.html(QWeb.render("ListView", this));

        // Head hook
        this.$element.find('#oe-list-add').click(this.do_add_record);
        this.$element.find('#oe-list-delete')
                .hide()
                .click(this.do_delete_selected);
        this.$element.find('thead').delegate('th[data-id]', 'click', function (e) {
            e.stopPropagation();

            self.dataset.sort($(this).data('id'));

            // TODO: should only reload content (and set the right column to a sorted display state)
            self.do_reload();
        });

        var $table = this.$element.find('table');
        this.list.move_to($table);

        this.view_manager.sidebar.set_toolbar(data.fields_view.toolbar);
    },
    /**
     * Fills the table with the provided records after emptying it
     *
     * TODO: should also re-load the table itself, as e.g. columns may have changed
     *
     * @param {Object} result filling result
     * @param {Array} [result.view] the new view (wrapped fields_view_get result)
     * @param {Array} result.records records the records to fill the list view with
     */
    do_fill_table: function(result) {
        if (result.view) {
            this.on_loaded({fields_view: result.view});
        }
        var records = result.records;

        this.rows.splice(0, this.rows.length);
        this.rows.push.apply(this.rows, records);

        // Keep current selected record, if it's still in our new search
        var current_record_id = this.dataset.ids[this.dataset.index];
        this.dataset.ids = _(records).chain().map(function (record) {
            return record.data.id.value;
        }).value();
        this.dataset.index = _.indexOf(this.dataset.ids, current_record_id);
        if (this.dataset.index < 0) {
            this.dataset.index = 0;
        }
        
        this.dataset.count = this.dataset.ids.length;
        var results = this.rows.length;
        this.$element.find('table')
            .find('.oe-pager-last').text(results).end()
            .find('.oe-pager-total').text(results);

        this.list.refresh();
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
     * @param {Number|null} index the record index (in the current dataset) to switch to
     * @param {String} [view="form"] the view type to switch to
     */
    select_record:function (index, view) {
        view = view || 'form';
        this.dataset.index = index;
        _.delay(_.bind(function () {
            if(this.view_manager) {
                this.view_manager.on_mode_switch(view);
            }
        }, this));
    },
    do_show: function () {
        this.$element.show();
        if (this.hidden) {
            this.do_reload();
            this.hidden = false;
        }
        this.view_manager.sidebar.refresh(true);
    },
    do_hide: function () {
        this.$element.hide();
        this.hidden = true;
    },
    /**
     * Reloads the search view based on the current settings (dataset & al)
     */
    do_reload: function () {
        // TODO: need to do 5 billion tons of pre-processing, bypass
        // DataSet for now
        //self.dataset.read_slice(self.dataset.fields, 0, self.limit,
        // self.do_fill_table);
        this.dataset.offset = 0;
        this.dataset.limit = false;
        return this.rpc('/base/listview/fill', {
            'model': this.dataset.model,
            'id': this.view_id,
            'context': this.dataset.context,
            'domain': this.dataset.domain,
            'sort': this.dataset.sort && this.dataset.sort()
        }, this.do_fill_table);
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
        var self = this;
        return this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: groupbys
        }, function (results) {
            // TODO: handle non-empty results.group_by with read_group
            self.dataset.context = results.context;
            self.dataset.domain = results.domain;
            if (results.group_by.length) {
                self.groups.datagroup = new openerp.base.DataGroup(
                        self.session, self.dataset.model,
                        results.domain, results.context,
                        results.group_by);
                self.$element.html(self.groups.render());
                return;
            }
            return self.do_reload();
        });
    },
    do_update: function () {
        var self = this;
        //self.dataset.read_ids(self.dataset.ids, self.dataset.fields, self.do_fill_table);
    },
    /**
     * Handles the signal to delete a line from the DOM
     *
     * @param {Array} ids the id of the object to delete
     */
    do_delete: function (ids) {
        if (!ids.length) {
            return;
        }
        var self = this;
        return $.when(this.dataset.unlink(ids)).then(function () {
            _(self.rows).chain()
                .map(function (row, index) {
                    return {
                        index: index,
                        id: row.data.id.value
                    };})
                .filter(function (record) {
                    return _.contains(ids, record.id);
                })
                .sort(function (a, b) {
                    // sort in reverse index order, so we delete from the end
                    // and don't blow up the following indexes (leading to
                    // removing the wrong records from the visible list)
                    return b.index - a.index;
                })
                .each(function (record) {
                    self.rows.splice(record.index, 1);
                });
            // TODO only refresh modified rows
            self.list.refresh();
        });
    },
    /**
     * Handles signal for the addition of a new record (can be a creation,
     * can be the addition from a remote source, ...)
     *
     * The default implementation is to switch to a new record on the form view
     */
    do_add_record: function () {
        this.notification.notify('Add', "New record");
        this.select_record(null);
    },
    /**
     * Handles deletion of all selected lines
     */
    do_delete_selected: function () {
        this.do_delete(
            this.list.get_selection());
    }
    // TODO: implement reorder (drag and drop rows)
});
openerp.base.ListView.List = Class.extend( /** @lends openerp.base.ListView.List# */{
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
    init: function (opts) {
        var self = this;
        // columns, rows, options

        this.options = opts.options;
        this.columns = opts.columns;
        this.rows = opts.rows;

        this.$_element = $('<tbody class="ui-widget-content">')
            .appendTo(document.body)
            .delegate('th.oe-record-selector', 'click', function (e) {
                e.stopPropagation();
                $(self).trigger('selected', [self.get_selection()]);
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
                  record_id = self.row_id($target.closest('tr'));

                $(self).trigger('action', [field, record_id]);
            })
            .delegate('tr', 'click', function (e) {
                e.stopPropagation();
                $(self).trigger(
                    'row_link',
                    [self.row_position(e.currentTarget),
                     self.row_id(e.currentTarget)]);
            });
    },
    move_to: function (element) {
        this.$current = this.$_element.clone(true).appendTo(element);
        this.render();
        return this;
    },
    render: function () {
        this.$current.empty().append($(QWeb.render('ListView.rows', this)));
        return this;
    },
    refresh: function () {
        this.render();
        return this;
    },
    /**
     * Gets the ids of all currently selected records, if any
     * @returns {Array} empty if no record is selected (or the list view is not selectable)
     */
    get_selection: function () {
        if (!this.options.selectable) {
            return [];
        }
        var rows = this.rows;
        return this.$current.find('th.oe-record-selector input:checked')
                .closest('tr').map(function () {
            return rows[$(this).prevAll().length].data.id.value;
        }).get();
    },
    /**
     * Returns the index of the row in the list of rows.
     *
     * @param {Object} row the selected row
     * @returns {Number} the position of the row in this.rows
     */
    row_position: function (row) {
        return $(row).prevAll().length;
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
    }
    // drag and drop
    // editable?
});
openerp.base.ListView.Groups = Class.extend( /** @lends openerp.base.ListView.Groups# */{
    /**
     * Grouped display for the ListView. Handles basic DOM events and interacts
     * with the :js:class:`~openerp.base.DataGroup` bound to it.
     *
     * Provides events similar to those of
     * :js:class:`~openerp.base.ListView.List`
     */
    init: function (opts) {
        this.options = opts.options;
        this.columns = opts.columns;
        this.datagroup = {};
    },
    make_level: function (datagroup) {
        var self = this, $root = $('<dl>');
        datagroup.list().then(function (list) {
            _(list).each(function (group, index) {
                var $title = $('<dt>')
                    .text(group.grouped_on + ': ' + group.value + ' (' + group.length + ')')
                    .appendTo($root);
                $title.click(function () {
                    datagroup.get(index, function (new_dataset) {
                        var $content = $('<ul>').appendTo(
                            $('<dd>').insertAfter($title));
                        new_dataset.read_slice([], null, null, function (records) {
                            _(records).each(function (record) {
                                $('<li>')
                                    .appendTo($content)
                                    .text(_(record).map(function (value, key) {
                                        return key + ': ' + value;
                                }).join(', '));
                            });
                        });
                    }, function (new_datagroup) {
                        console.log(new_datagroup);
                        $('<dd>')
                            .insertAfter($title)
                            .append(self.make_level(new_datagroup));
                    });
                });
            });
        });
        return $root;
    },
    render: function () {
        return this.make_level(this.datagroup);
    }
});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
