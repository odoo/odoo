openerp.base.list = function (openerp) {
'use strict';
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
        this.view_manager = view_manager;
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;

        this.columns = [];

        this.options = _.extend({}, this.defaults, options || {});

        this.groups = new openerp.base.ListView.Groups(this, {
            options: this.options,
            columns: this.columns
        });
        $(this.groups).bind({
            'selected': function (e, selection) {
                self.$element.find('#oe-list-delete')
                    .toggle(!!selection.length);
            },
            'deleted': function (e, ids) {
                self.do_delete(ids);
            },
            'action': function (e, action_name, id, callback) {
                var action = _.detect(self.columns, function (field) {
                    return field.name === action_name;
                });
                if (!action) { return; }
                self.execute_action(
                    action, self.dataset, self.session.action_manager,
                    id, function () {
                        if (callback) {
                            callback();
                        }
                });
            },
            'row_link': function (e, index, id, dataset) {
                _.extend(self.dataset, {
                    domain: dataset.domain,
                    context: dataset.context
                }).read_slice([], null, null, function () {
                    self.select_record(index);
                });
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
            toolbar: this.view_manager ? !!this.view_manager.sidebar : false
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
     * @param {Array} columns columns to move to the front (and make visible)
     */
    on_loaded: function(data, columns) {
        var self = this;
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);
        this.name = "" + this.fields_view.arch.attrs.string;

        this.setup_columns(this.fields_view.fields, columns);

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

        // sidebar stuff
        if (this.view_manager && this.view_manager.sidebar) {
            this.view_manager.sidebar.set_toolbar(data.fields_view.toolbar);
        }
    },
    /**
     * Sets up the listview's columns: merges view and fields data, move
     * grouped-by columns to the front of the columns list and make them all
     * visible.
     *
     * @param {Object} fields fields_view_get's fields section
     * @param {Array} groupby_columns columns the ListView is grouped by
     */
    setup_columns: function (fields, groupby_columns) {
        var self = this;
        var domain_computer = openerp.base.form.compute_domain;

        var noop = function () { return {}; };
        var field_to_column = function (field) {
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
                column.attrs_for = noop;
            }
            return column;
        };
        
        this.columns.splice(0, this.columns.length);
        this.columns.push.apply(
                this.columns,
                _(this.fields_view.arch.children).map(field_to_column));

        _(groupby_columns).each(function (column_id, index) {
            var column_index = _(self.columns).chain()
                    .pluck('id').indexOf(column_id).value();
            var column = self.columns.splice(column_index, 1)[0];
            delete column.invisible;
            self.columns.splice(index, 0, column);
        });

        this.visible_columns = _.filter(this.columns, function (column) {
            return column.invisible !== '1';
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
            this.$element.find('table').append(
                this.groups.apoptosis().render());
            this.hidden = false;
        }
    },
    do_hide: function () {
        this.$element.hide();
        this.hidden = true;
    },
    /**
     * Reloads the search view based on the current settings (dataset & al)
     *
     * @param {Array} [primary_columns] columns to bring to the front of the
     *                                  sequence
     */
    do_reload: function (primary_columns) {
        // TODO: need to do 5 billion tons of pre-processing, bypass
        // DataSet for now
        //self.dataset.read_slice(self.dataset.fields, 0, self.limit,
        // self.do_fill_table);
        var self = this;
        this.dataset.offset = 0;
        this.dataset.limit = false;
        return this.rpc('/base/listview/fill', {
            'model': this.dataset.model,
            'id': this.view_id,
            'context': this.dataset.context,
            'domain': this.dataset.domain,
            'sort': this.dataset.sort && this.dataset.sort()
        }, function (result) {
            if (result.view) {
                self.on_loaded({fields_view: result.view}, primary_columns);
            }
        });
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
            self.dataset.context = results.context;
            self.dataset.domain = results.domain;
            self.groups.datagroup = new openerp.base.DataGroup(
                self.session, self.dataset.model,
                results.domain, results.context,
                results.group_by);
            self.do_reload(results.group_by).then(function () {
                self.$element.find('table').append(self.groups.render());
            });
        });
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
        this.do_delete(this.groups.get_selection());
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
        this.dataset = opts.dataset;
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
                     self.row_id(e.currentTarget),
                     self.dataset]);
            });
    },
    render: function () {
        if (this.$current) {
            this.$current.remove();
        }
        this.$current = this.$_element.clone(true);
        this.$current.empty().append($(QWeb.render('ListView.rows', this)));
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
    },
    /**
     * Death signal, cleans up list
     */
    apoptosis: function () {
        if (!this.$current) { return; }
        this.$current.remove();
        this.$current = null;
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
    init: function (view, opts) {
        this.view = view;
        this.options = opts.options;
        this.columns = opts.columns;
        this.datagroup = {};

        this.sections = [];
        this.children = {};
    },
    pad: function ($row) {
        if (this.options.selectable) {
            $row.append('<td>');
        }
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
        var red_letter_tbody = $row.closest('tbody')[0];

        var $next_siblings = $row.nextAll();
        if ($next_siblings.length) {
            var $root_kanal = $('<tbody>').insertAfter(red_letter_tbody);

            $root_kanal.append($next_siblings);
            this.elements.splice(
                _.indexOf(this.elements, red_letter_tbody),
                0,
                $root_kanal[0]);
        }
        return red_letter_tbody;
    },
    open_group: function (e, group) {
        var row = e.currentTarget;

        if (this.children[group.value]) {
            this.children[group.value].apoptosis();
            delete this.children[group.value];
        }
        var prospekt = this.children[group.value] = new openerp.base.ListView.Groups(this.view, {
            options: this.options,
            columns: this.columns
        });
        this.bind_child_events(prospekt);
        prospekt.datagroup = group;
        prospekt.render().insertAfter(
            this.point_insertion(row));
        $(row).find('span.ui-icon')
                .removeClass('ui-icon-triangle-1-e')
                .addClass('ui-icon-triangle-1-s');
    },
    render_groups: function (datagroups) {
        var self = this;
        var placeholder = this.make_fragment();
        _(datagroups).each(function (group) {
            var $row = $('<tr>').click(function (e) {
                if (!$row.data('open')) {
                    $row.data('open', true);
                    self.open_group(e, group);
                } else {
                    $row.removeData('open')
                        .find('span.ui-icon')
                            .removeClass('ui-icon-triangle-1-s')
                            .addClass('ui-icon-triangle-1-e');
                    _(self.children).each(function (child) {child.apoptosis();});
                }
            });
            placeholder.appendChild($row[0]);
            self.pad($row);

            _(self.columns).chain()
                .filter(function (column) {return !column.invisible;})
                .each(function (column) {
                    if (column.id === group.grouped_on) {
                        $('<th>')
                            .text(_.sprintf("%s (%d)",
                                group.value instanceof Array ? group.value[1] : group.value,
                                group.length))
                            .prepend('<span class="ui-icon ui-icon-triangle-1-e">')
                            .appendTo($row);
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
        });
        return placeholder;
    },
    bind_child_events: function (child) {
        var $this = $(this),
             self = this;
        $(child).bind('selected', function (e) {
            // can have selections spanning multiple links
            $this.trigger(e, [self.get_selection()]);
        }).bind('action', function (e, name, id, callback) {
            if (!callback) {
                callback = function () {
                    var $prev = child.$current.prev();
                    if (!$prev.is('tbody')) {
                        // ungrouped
                        $(self.elements[0]).replaceWith(self.render());
                    } else {
                        // ghetto reload child (and its siblings)
                        $prev.children().last().click();
                    }
                };
            }
            $this.trigger(e, [name, id, callback]);
        }).bind('deleted row_link', function (e) {
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
            list = new openerp.base.ListView.List({
                options: this.options,
                columns: this.columns,
                dataset: dataset,
                rows: rows
            });
        this.bind_child_events(list);

        var d = new $.Deferred();
        this.view.rpc('/base/listview/fill', {
            model: dataset.model,
            id: this.view.view_id,
            context: dataset.context,
            domain: dataset.domain,
            sort: dataset.sort && dataset.sort()
        }, function (result) {
            rows.splice(0, rows.length);
            rows.push.apply(rows, result.records);
            list.render();
            d.resolve(list);
        });
        return d.promise();
    },
    render: function () {
        var self = this;
        var $element = $('<tbody>');
        this.elements = [$element[0]];
        this.datagroup.list(function (groups) {
            $element[0].appendChild(
                self.render_groups(groups));
        }, function (dataset) {
            self.render_dataset(dataset).then(function (list) {
                self.children[null] = list;
                self.elements =
                    [list.$current.replaceAll($element)[0]];
            });
        });
        return $element;
    },
    /**
     * Returns the ids of all selected records for this group
     */
    get_selection: function () {
        return _(this.children).chain()
            .map(function (child) {
                return child.get_selection();
            })
            .flatten()
            .value();
    },
    apoptosis: function () {
        _(this.children).each(function (child) {
            child.apoptosis();
        });
        $(this.elements).remove();
        return this;
    }
});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
