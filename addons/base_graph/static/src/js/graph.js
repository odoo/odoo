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
                    this.group_field = this.fields_view.arch.children[fld].attrs.name;
            }
            else {
                this.chart_info_fields.push(this.fields_view.arch.children[fld].attrs.name);
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

        for(res in result) {
            for(fld in result[res]) {
                if (fld != 'state') {
                    if (typeof result[res][fld] == 'object') {
                        result[res][fld] = result[res][fld][result[res][fld].length - 1];
                    }

                }
            }
        }

        if(this.chart == 'bar') {
           	return this.schedule_bar(result, "barchart")
        } else if(this.chart == "pie") {
            return this.schedule_pie(result, "piechart");
        }

    },

    schedule_bar: function(result, container) {
        var self = this;
        var view_chart = this.orientation == 'horizontal'? 'barH' : this.chart || 'bar';

        var bar_chart = new dhtmlxchartChart({
           view: view_chart,
           container: container,
           gradient: "3d",
           border: false,
           width: 30,
           origin:0,
	       legend: {
                align:"right",
			    valign:"top",
			    marker:{
				    type:"round",
				    width:12
			        },
                template: self.fields[self.operator_field]['string']

            }
        });

        if(self.group_field) {
	        bar_chart.define("group",{
	            by:"#"+self.chart_info_fields[0]+"#",
	            map:{
						map_fld:["#"+self.operator_field+"#", "sum"]
					}
	         });
            bar_chart.define("value","#map_fld#");
            bar_chart.define("label","#map_fld#");
        }
        else{
        	bar_chart.define("value","#"+self.operator_field+"#");
        	bar_chart.define("label","#"+self.chart_info_fields[0]+"#");
        }

        if(view_chart == 'barH') {
            bar_chart.define("xAxis",{
                title: this.fields[this.operator_field]['string'],
                lines: true
            });

            bar_chart.define("yAxis",{
                template: "#id#",
                title:  this.fields[this.chart_info_fields[0]]['string'],
                lines: true
            });

        } else {
            bar_chart.define("xAxis",{
                template:"#"+this.chart_info_fields[0]+"#",
                title: this.fields[this.chart_info_fields[0]]['string'],
                lines: true
            });

            bar_chart.define("yAxis",{
                title: this.fields[this.operator_field]['string'],
	            lines: true,
            });

        }
		bar_chart.parse(result,"json");

    },

    schedule_pie: function(result, container) {
        var chart =  new dhtmlxchartChart({
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

    do_search: function(domains, contexts, groupbys) {
        var self = this;

        this.rpc('/base/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: groupbys
        }, function (results) {
            // TODO: handle non-empty results.group_by with read_group
            self.dataset.context = self.context = results.context;
            self.dataset.domain = self.domain = results.domain;
            self.dataset.read_slice(self.fields, 0, self.limit,function(result){
                self.schedule_chart(result)
            });
        });

    },

});

// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them

};

// vim:et fdc=0 fdl=0:
