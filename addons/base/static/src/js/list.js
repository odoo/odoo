
openerp.base.list = function (openerp) {

openerp.base.views.add('list', 'openerp.base.ListView');
openerp.base.ListView = openerp.base.Controller.extend({
    init: function(view_manager, session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.view_manager = view_manager;
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;

        this.columns = [];
        this.rows = [];
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
                'tr', 'click', this.on_select_row);

        // sidebar stuff
        if (this.view_manager.sidebar)
            this.view_manager.sidebar.load_multi_actions();
    },
    do_fill_table: function(records) {
        this.rows = records;

        var table = this.$element.find('table');
        // remove all data lines
        table.find('tr:first').nextAll().remove();
        // add new content
        table.append(QWeb.render("ListView.rows", {
                columns: this.columns, rows: this.rows}));
    },
    on_select_row: function (event) {
        // count number of preceding siblings to line clicked, that's the one
        // we want (note: line 0 is title row, so remove 1 for actual row
        // index)
        var row = this.rows[$(event.currentTarget).prevAll().length - 1];

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
    }
});

openerp.base.TreeView = openerp.base.Controller.extend({
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
