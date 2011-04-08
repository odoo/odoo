/*---------------------------------------------------------
 * OpenERP base_graph
 *---------------------------------------------------------*/

openerp.base.graph = function (openerp) {
openerp.base.views.add('graph', 'openerp.base.GraphView');
openerp.base.GraphView = openerp.base.Controller.extend({

	init: function(view_manager, session, element_id, dataset, view_id) {

        this._super(session, element_id);
        this.view_manager = view_manager;
        this.dataset = dataset;
        this.model = dataset.model;
        this.view_id = view_id;
        this.fields_views = {};
        this.widgets = {};
        this.widgets_counter = 0;
        this.fields = {};
        this.datarecord = {};
        this.calendar_fields = {};
    },
    do_show: function () {
        // TODO: re-trigger search
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    },
    start: function() {
        this.rpc("/base_graph/graphview/load", {"model": this.model, "view_id": this.view_id}, this.on_loaded);
    },
    on_loaded: function(data) {
        this.fields_view = data.fields_view;
		var self = this;
		this.name = this.fields_view.name || this.fields_view.arch.attrs.string;
		this.view_id = this.fields_view.view_id;
		this.fields['partner_id'] = this.fields_view.arch.children[0].attrs.name;
		this.fields['total'] = this.fields_view.arch.children[1].attrs.name;

		this.rpc('/base_graph/graphview/get_events',
				{'model': this.model,
				'fields': this.fields
				},
				function(res) {
					self.create_graph(res);
				})
        this.$element.html(QWeb.render("GraphView", {"view": this, "fields_view": this.fields_view}));
	},
	create_graph: function(res) {
		var result = res.result;

	    var barChart1 = new dhtmlXChart({
	    	view:"bar",
			container:"chart1",
	        value:"#amount_total#",
			color:"#9abe00",
            width:50,
            tooltip: "#partner_id#",
            xAxis:{
				title:"Partner",
				template:"#partner_id#"
			},
			yAxis:{
                start:0,
                end:10000,
                step:1000,
				title:"Total"
			}
		});
	    barChart1.parse(result, "json");
	},


});

// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them

};

// vim:et fdc=0 fdl=0:
