
openerp.addons.base.form = function (openerp) {

openerp.base.ListView = openerp.base.Controller.extend({
    init: function(session, element_id, dataset, view_id) {
        this._super(session, element_id);
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.name = "";

        this.cols = [];

        this.$table = null;
        this.colnames = [];
        this.colmodel = [];

        this.event_loading = false; // TODO in the future prevent abusive click by masking
    },
    start: function() {
        //this.log('Starting ListView '+this.model+this.view_id)
        this.rpc("/base/listview/load", {"model": this.model, "view_id":this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
        //this.log(this.fields_view);
        this.name = "" + this.fields_view.arch.attrs.string;
        this.$element.html(QWeb.render("ListView", {"fields_view": this.fields_view}));
        this.$table = this.$element.find("table");
        this.cols = [];
        this.colnames = [];
        this.colmodel = [];
        // TODO uss a object for each col, fill it with view and fallback to dataset.model_field
        var tree = this.fields_view.arch.children;
        for(var i = 0; i < tree.length; i++)  {
            var col = tree[i];
            if(col.tag == "field") {
                this.cols.push(col.attrs.name);
                this.colnames.push(col.attrs.name);
                this.colmodel.push({ name: col.attrs.name, index: col.attrs.name });
            }
        }
        this.dataset.fields = this.cols;
        this.dataset.on_fetch.add(this.do_fill_table);
        
        var width = this.$element.width();
        this.$table.jqGrid({
            datatype: "local",
            height: "100%",
            rowNum: 100,
            //rowList: [10,20,30],
            colNames: this.colnames,
            colModel: this.colmodel,
            //pager: "#plist47",
            viewrecords: true,
            caption: this.name
        }).setGridWidth(width);

        var self = this;
        $(window).bind('resize', function() {
            self.$element.children().hide();
            self.$table.setGridWidth(self.$element.width());
            self.$element.children().show();
        }).trigger('resize');
    },
    do_fill_table: function(records) {
        this.log("do_fill_table");

        this.$table
            .clearGridData()
            .addRowData('id', _.map(records, function (record) {
                return record.values;
            }));

    }
});

openerp.base.TreeView = openerp.base.Controller.extend({
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
