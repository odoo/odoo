/*---------------------------------------------------------
 * OpenERP base_graph
 *---------------------------------------------------------*/

openerp.base_graph = function (openerp) {
QWeb.add_template('/base_graph/static/src/xml/base_graph.xml');
openerp.base.views.add('graph', 'openerp.base_graph.GraphView');
openerp.base_graph.GraphView = openerp.base.Controller.extend({

	init: function(view_manager, session, element_id, dataset, view_id) {

        this._super(session, element_id);
        this.view_manager = view_manager;
        this.dataset = dataset;
        this.model = this.dataset.model;
        this.view_id = view_id;
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
        var self = this;
        this.fields_view = data.fields_view;
		this.name = this.fields_view.name || this.fields_view.arch.attrs.string;
		this.view_id = this.fields_view.view_id;
        this.chart = this.fields_view.arch.attrs.type || 'pie';
        this.fields = this.fields_view.fields;
        this.chart_info_fields = [];
        this.operator_field = '';
        this.group_field = '';
        this.orientation = this.fields_view.arch.attrs.orientation || '';
        for(fld in this.fields_view.arch.children) {
            if (this.fields_view.arch.children[fld].attrs.operator) {
                this.operator_field = this.fields_view.arch.children[fld].attrs.name;
            }
            else if (this.fields_view.arch.children[fld].attrs.group) {
                    this.group_field = this.fields_view.arch.children[fld].attrs.name
            }
            else {
                this.chart_info_fields.push(this.fields_view.arch.children[fld].attrs.name)
            }
        }
        
        this.load_chart();
	},
    
    load_chart: function() {
        var self = this;
        this.dataset.read_ids(
            this.dataset.ids,
            this.fields,
            function(result) {
                self.schedule_chart(result)
            }
        )
    },
    
    schedule_chart: function(result) {
        
        this.$element.html(QWeb.render("GraphView", {"fields_view": this.fields_view, "chart": this.chart}));
        
        console.log('fields view >>>>>>',this.fields_view)
        
        for(res in result) {
            for(fld in result[res]) {
                if(typeof result[res][fld] == 'object') {
                    result[res][fld] = result[res][fld][result[res][fld].length - 1]
                }
            }
        }
        if(this.chart == 'bar') {
            var xAxis = {};
            var yAxis = {};
            
            if (this.orientation && this.orientation == 'horizontal') {
                this.chart = "barH";
                xAxis:{template:"#"+this.operator_field+"#"};
			    yAxis:{title: this.chart_info_fields[0]};
            } else {
                xAxis:{template:"#"+this.chart_info_fields[0]+"#"};
			    yAxis:{title: this.operator_field};
            }
            return this.schedule_bar(result, xAxis, yAxis, "barchart")
        } else if(this.chart == "pie") {
            return this.schedule_pie(result, "piechart");
        }
        
    },
    
    
    schedule_bar: function(result, xAxis, yAxis, container) {
        var chart = new dhtmlXChart({
            view: this.chart,
            container: container,
            value: "#"+this.operator_field+"#",
            color:"#d2ed7e",
            width:30,
            gradient:"3d",
            tooltip: "#"+this.chart_info_fields[0]+"#",
            xAxis: xAxis,
			yAxis: yAxis,
            legend: {
                align:"right",
			    valign:"top",
			    marker:{
				    type:"round",
				    width:12
			        },
                template:"#"+this.chart_info_fields[0]+"#"
            }
        });
        if(this.group_field) {
//            var map_fld = this.chart_info_fields[0];
//            chart.group({
//               by: "#"+this.group_field+"#",
//               map:{
//					map_fld :["#"+this.operator_field+"#", "sum"]
//				} 
//            });
        }
        chart.parse(result, "json");
    },
    
    schedule_pie: function(result, container) {
        var chart =  new dhtmlXChart({
    		view:"pie",
    		container:container,
    		value:"#"+this.operator_field+"#",
    		color:"#d2ed7e",
    		label:"#"+this.chart_info_fields[0]+"#",
    		pieInnerText:"<b>#"+this.operator_field+"#</b>",
    		gradient:"3d",
            legend: {
                width: 100,
                align:"right",
			    valign:"top",
			    marker:{
				    type:"round",
				    width:12
			        },
                template:"#"+this.chart_info_fields[0]+"#"
            }
    	});
    	chart.parse(result,"json");
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
