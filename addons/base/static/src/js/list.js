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
        return this.rpc("/base/listview/load", {"model": this.model, "view_id":this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);
        this.name = "" + this.fields_view.arch.attrs.string;

        var fields = this.fields_view.fields;
        this.columns = _(this.fields_view.arch.children).chain()
            .map(function (field) {
                var name = field.attrs.name;
                return _.extend({id: name, tag: field.tag}, field.attrs, fields[name]);
            }).value();

        this.$element.html(QWeb.render("ListView", this));
        this.$element.find('table').delegate(
                'th.oe-record-selector', 'click', function (e) {
                    // A click in the selection cell should not activate the
                    // linking feature
                    e.stopImmediatePropagation();
        });
        this.$element.find('table').delegate(
                'td.oe-record-delete button', 'click', this.do_delete);
        this.$element.find('table').delegate(
                'tr', 'click', this.on_select_row);

        // sidebar stuff
        if (this.view_manager.sidebar)
            this.view_manager.sidebar.load_multi_actions();
    },
    /**
     * Fills the table with the provided records after emptying it
     *
     * @param {Array} records the records to fill the list view with
     * @returns {Promise} promise to the end of view rendering (list views are asynchronously filled for improved responsiveness)
     */
    do_fill_table: function(records) {
        this.rows = records;

        var $table = this.$element.find('table');
        // remove all data lines
        $table.find('tbody').remove();

        // add new content
        var columns = this.columns,
            rows = this.rows,
            options = this.options;

        // Paginate by groups of 50 for rendering
        var PAGE_SIZE = 50,
            bodies_count = Math.ceil(this.rows.length / PAGE_SIZE),
            body = 0,
            $body = $('<tbody>').appendTo($table);

        var render_body = function () {
            var rendered = $.Deferred();
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
            return rendered.promise();
        };
        return render_body();
    },
    on_select_row: function (event) {
        var $target = $(event.currentTarget);
        if (!$target.parent().is('tbody')) {
            return;
        }
        // count number of preceding siblings to line clicked
        var row = this.rows[$target.prevAll().length];

        var index = _.indexOf(this.dataset.ids, row.id);
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
            self.dataset.fetch(self.dataset.fields, 0, self.limit, self.do_fill_table);
        });
    },
    do_update: function () {
        var self = this;
        self.dataset.fetch(self.dataset.fields, 0, self.limit, self.do_fill_table);
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
