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
		this.fields['id'] = this.fields_view.arch.children[0].attrs.name;
		this.fields['total'] = this.fields_view.arch.children[1].attrs.name;
		this.graph_type = this.fields_view.arch.attrs.type;

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
		//if (this.graph_type == "bar"){
	    var barChart = new dhtmlXChart({
	    	view:"bar",
			container:"barchart",
	        value:"#"+this.fields['total']+"#",
			color:"#9abe00",
            width:40,
            tooltip: "#"+this.fields['id']+"#",
            xAxis:{
				template:"#"+this.fields['id']+"#"
			},
			yAxis:{
				title: "Total"
			}
		});
	    barChart.parse(res, "json");
		//}
		var pieChart = new dhtmlXChart({
	    	view: "pie",
	        container: "piechart",
	        value: "#"+this.fields['total']+"#",
	        label: "#"+this.fields['id']+"#",
	        pieInnerText: "<b>#"+this.fields['total']+"#</b>",
	        gradient: true,
        	radius: 90,
        	x: 280,
        	y: 150
		});
	    pieChart.parse(res, "json");

	    /*static data for stackedbar chart*/
	    var data = [{
		    total: "2.0",
		    total1: "0.0",
		    stage: "Lost"
		}, {
		    total: "1.0",
		    total1: "2.0",
		    stage: "Negotiation"
		}, {
		    total: "4.0",
		    total1: "2.0",
		    stage: "New"
		}, {
		    total: "3.0",
		    total1: "0.0",
		    stage: "Proposition"
		}, {
		    total: "1.0",
		    total1: "1.0",
		    stage: "Qualification"
		}, {
		    total: "1.0",
		    total1: "0.0",
		    stage: "Won"
		}];

	    var stackedChart = new dhtmlXChart({
		    view: "stackedBar",
	        container: "stackedchart",
	        value: "#total#",
	        label: "#total#",
	        width: 60,
	        tooltip: {
	            template: "#total#"
	        },
	        xAxis: {
	            template: "#stage#"
	        },
	        yAxis: {
	            title: "User"
	        },
	        gradient: "3d",
	        color: "#66cc33",
	        legend: {
	            values: [{
			                text: "Administrator",
			                color: "#66cc33"
			            }, {
			                text: "Demo User",
			                color: "#ff9933"
			            }],
			            valign: "top",
			            align: "right",
			            width: 120,
			            layout: "y",
			            marker: {
			                width: 15,
			                type: "round"
			            }
			        }
		});
	    stackedChart.addSeries({
	        value: "#total1#",
	        color: "#ff9933",
	        label: "#total1#",
	        tooltip: {
	            template: "#total1#"
	        }
	    });
		stackedChart.parse(data, "json");
	},


});

// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them

};

// vim:et fdc=0 fdl=0:
