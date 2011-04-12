openerp.base.list = function (openerp) {
openerp.base.views.add('list', 'openerp.base.ListView');
openerp.base.ListView = openerp.base.Controller.extend(
    /** @lends openerp.base.ListView# */ {
    defaults: {
        // records can be selected one by one
        'selectable': true,
        // list rows can be deleted
        'deletable': true,
        // whether the column headers should be displayed
        'header': true
    },
    /**
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
     */
    init: function(view_manager, session, element_id, dataset, view_id, options) {
        this._super(session, element_id);
        this.view_manager = view_manager;
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;

        this.columns = [];
        this.rows = [];

        this.options = _.extend({}, this.defaults, options || {});
    },
    start: function() {
        //this.log('Starting ListView '+this.model+this.view_id)
        return this.rpc("/base/listview/load", {"model": this.model, "view_id":this.view_id,
            toolbar:!!this.view_manager.sidebar}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);
        this.name = "" + this.fields_view.arch.attrs.string;

        var fields = this.fields_view.fields;
        var domain_computer = openerp.base.form.compute_domain;
        this.columns = _(this.fields_view.arch.children).chain()
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
            }).value();

        this.visible_columns = _.filter(this.columns, function (column) {
            return column.invisible !== '1';
        });
        this.$element.html(QWeb.render("ListView", this));

        // Head hook
        this.$element.find('#oe-list-delete').click(this.do_delete_selected);

        // Cell events
        this.$element.find('table').delegate(
                'th.oe-record-selector', 'click', function (e) {
                    // A click in the selection cell should not activate the
                    // linking feature
                    e.stopImmediatePropagation();
        });
        this.$element.find('table').delegate(
                'td.oe-record-delete button', 'click', this.do_delete);

        // Global rows handlers
        this.$element.find('table').delegate(
                'tr', 'click', this.on_select_row);

        // sidebar stuff
        if (this.view_manager.sidebar) {
            this.view_manager.sidebar.set_toolbar(data.fields_view.toolbar);
        }
    },
    /**
     * Fills the table with the provided records after emptying it
     *
     * @param {Array} records the records to fill the list view with
     * @returns {Promise} promise to the end of view rendering (list views are asynchronously filled for improved responsiveness)
     */
    do_fill_table: function(records) {
        this.rows = records;
        this.dataset.ids = _(records).chain().map(function (record) {
            return record.data.id.value;
        }).value();

        var $table = this.$element.find('table');
        // remove all data lines
        var $old_body = $table.find('tbody');

        // add new content
        var columns = this.columns,
            rows = this.rows,
            options = this.options;

        // Paginate by groups of 50 for rendering
        var PAGE_SIZE = 50,
            bodies_count = Math.ceil(this.rows.length / PAGE_SIZE),
            body = 0,
            $body = $('<tbody>').appendTo($table);

        var rendered = $.Deferred();
        var render_body = function () {
            setTimeout(function () {
                $body.append(
                    QWeb.render("ListView.rows", {
                        columns: columns,
                        rows: rows.slice(body*PAGE_SIZE, (body+1)*PAGE_SIZE),
                        options: options
                }));
                ++body;
                if (body < bodies_count) {
                    render_body();
                } else {
                    rendered.resolve();
                }
            }, 0);
        };
        render_body();

        return rendered.promise().then(function () {
            $old_body.remove();
        });
    },
    on_select_row: function (event) {
        var $target = $(event.currentTarget);
        if (!$target.parent().is('tbody')) {
            return;
        }
        // count number of preceding siblings to line clicked
        var row = this.rows[$target.prevAll().length];

        var index = _.indexOf(this.dataset.ids, row.data.id.value);
        if (index == undefined || index === -1) {
            return;
        }
        this.dataset.index = index;
        _.delay(_.bind(function () {
            this.view_manager.on_mode_switch('form');
        }, this));

    },
    do_show: function () {
        // TODO: re-trigger search
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    },
    do_search: function (domains, contexts, groupbys) {
        var self = this;
        this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: groupbys
        }, function (results) {
            // TODO: handle non-empty results.group_by with read_group
            self.dataset.context = results.context;
            self.dataset.domain = results.domain;
            // TODO: need to do 5 billion tons of pre-processing, bypass
            // DataSet for now
            //self.dataset.read_slice(self.dataset.fields, 0, self.limit,
            // self.do_fill_table);
            self.rpc('/base/listview/fill', {
                'model': self.dataset.model,
                'id': self.view_id,
                'context': results.context,
                'domain': results.domain
            }, self.do_fill_table);
        });
    },
    do_update: function () {
        var self = this;
        self.dataset.read_ids(self.dataset.ids, self.dataset.fields, self.do_fill_table);
    },
    /**
     * Handles the signal to delete a line from the DOM
     *
     * @param e
     */
    do_delete: function (e) {
        // don't link to forms
        e.stopImmediatePropagation();
        this.dataset.unlink(
            [this.rows[$(e.currentTarget).closest('tr').prevAll().length].id]);
    },
    /**
     * Handles deletion of all selected lines
     */
    do_delete_selected: function () {
        var selection = this.get_selection();
        if (selection.length) {
            this.dataset.unlink(selection);
        }
    },
    /**
     * Gets the ids of all currently selected records, if any
     * @returns a list of ids, empty if no record is selected (or the list view is not selectable
     */
    get_selection: function () {
        if (!this.options.selectable) {
            return [];
        }
        var rows = this.rows;
        return this.$element.find('th.oe-record-selector input:checked')
                .closest('tr').map(function () {
            return rows[$(this).prevAll().length].id;
        }).get();
    }
});

openerp.base.TreeView = openerp.base.Controller.extend({
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
