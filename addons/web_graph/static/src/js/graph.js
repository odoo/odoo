/*---------------------------------------------------------
 * OpenERP web_graph
 *---------------------------------------------------------*/

openerp.web_graph = function (openerp) {
var COLOR_PALETTE = [
    '#cc99ff', '#ccccff', '#48D1CC', '#CFD784', '#8B7B8B', '#75507b',
    '#b0008c', '#ff0000', '#ff8e00', '#9000ff', '#0078ff', '#00ff00',
    '#e6ff00', '#ffff00', '#905000', '#9b0000', '#840067', '#9abe00',
    '#ffc900', '#510090', '#0000c9', '#009b00', '#75507b', '#3465a4',
    '#73d216', '#c17d11', '#edd400', '#fcaf3e', '#ef2929', '#ff00c9',
    '#ad7fa8', '#729fcf', '#8ae234', '#e9b96e', '#fce94f', '#f57900',
    '#cc0000', '#d400a8'];

var QWeb = openerp.web.qweb;
QWeb.add_template('/web_graph/static/src/xml/web_graph.xml');
openerp.web.views.add('graph', 'openerp.web_graph.GraphView');
openerp.web_graph.GraphView = openerp.web.View.extend({

    init: function(parent, dataset, view_id) {
        this._super(parent);
        this.view_manager = parent;
        this.dataset = dataset;
        this.dataset_index = 0;
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
        var self = this;
        this._super();
        return $.when(
            new openerp.web.DataSet(this, this.model).call('fields_get', []),
            this.rpc('/web/view/load', {
                model: this.model,
                view_id: this.view_id,
                view_type: 'graph'
            })).then(function (fields_result, view_result) {
                self.on_loaded({
                    all_fields: fields_result[0],
                    fields_view: view_result[0]
                });
        });
    },
    on_loaded: function(data) {
        this.all_fields = data.all_fields;
        this.fields_view = data.fields_view;
        this.name = this.fields_view.name || this.fields_view.arch.attrs.string;
        this.view_id = this.fields_view.view_id;
        this.chart = this.fields_view.arch.attrs.type || 'pie';
        this.fields = this.fields_view.fields;
        this.chart_info_fields = [];
        this.operator_field = '';
        this.operator_field_one = '';
        this.operator = [];
        this.group_field = [];
        this.orientation = this.fields_view.arch.attrs.orientation || '';
        _.each(this.fields_view.arch.children, function (field) {
            if (field.attrs.operator) {
                this.operator.push(field.attrs.name);
            }
            else if (field.attrs.group) {
                this.group_field.push(field.attrs.name);
            }
            else {
                this.chart_info_fields.push(field.attrs.name);
            }
        }, this);

        this.operator_field = this.operator[0];
        if(this.operator.length > 1){
            this.operator_field_one = this.operator[1];
        }
        if(this.operator == ''){
            this.operator_field = this.chart_info_fields[1];
        }
        this.chart_info = this.chart_info_fields[0];
        this.x_title = this.fields[this.chart_info_fields[0]]['string'];
        this.y_title = this.fields[this.operator_field]['string'];
        this.load_chart();
    },

    load_chart: function(data) {
        var self = this;
        var domain = false;
        if(data){
            this.x_title = this.all_fields[this.chart_info_fields]['string'];
            this.y_title = this.all_fields[this.operator_field]['string'];
            self.schedule_chart(data);
        }else{
            if(! _.isEmpty(this.view_manager.dataset.domain)){
                domain = this.view_manager.dataset.domain;
            }else if(! _.isEmpty(this.view_manager.action.domain)){
                domain = this.view_manager.action.domain;
            }
            this.dataset.domain = domain;
            this.dataset.context = this.view_manager.dataset.context;
            this.dataset.read_slice(_(this.fields).keys(),{}, function(res) {
                self.schedule_chart(res);
            });
        }
    },

    schedule_chart: function(results) {
        this.$element.html(QWeb.render("GraphView", {"fields_view": this.fields_view, "chart": this.chart,'element_id': this.element_id}));

        _.each(results, function (result) {
            _.each(result, function (field_value, field_name) {
                if (typeof field_value == 'object') {
                    result[field_name] = field_value[field_value.length - 1];
                }
                if (typeof field_value == 'string') {
                    var choices = this.all_fields[field_name]['selection'];
                    _.each(choices, function (choice) {
                        if (field_value == choice[0]) {
                            result[field_name] = choice;
                        }
                    });
                }
            }, this);
        }, this);

        var graph_data = {};
        _.each(results, function (result) {
            var group_key = [];
            if(this.group_field.length){
                _.each(this.group_field, function (res) {
                        result[res] = (typeof result[res] == 'object') ? result[res][1] : result[res];
                        group_key.push(result[res]);
                });
            }else{
                group_key.push(result[this.group_field]);
            }
            var column_key = result[this.chart_info_fields] + "_" + group_key;
            var column_descriptor = {};
            if (graph_data[column_key] == undefined) {
                column_descriptor[this.operator_field] = result[this.operator_field];
                if (this.operator.length > 1) {
                    column_descriptor[this.operator_field_one] = result[this.operator_field_one];
                }
                column_descriptor[this.chart_info_fields] = result[this.chart_info_fields];
                if(this.group_field.length){
                    _.each(this.group_field, function (res) {
                        column_descriptor[res] = (typeof result[res] == 'object') ? result[res][1] : result[res];
                    });
                }
            } else {
                column_descriptor = graph_data[column_key];
                column_descriptor[this.operator_field] += result[this.operator_field];
                if (this.operator.length > 1) {
                    column_descriptor[this.operator_field_one] += result[this.operator_field_one];
                }
            }
            graph_data[column_key] = column_descriptor;
        }, this);

        if (this.chart == 'bar') {
            return this.schedule_bar(_.values(graph_data));
        } else if (this.chart == "pie") {
            return this.schedule_pie(_.values(graph_data));
        }
    },

    schedule_bar: function(results) {
        var self = this;
        var view_chart = '';
        var group_list = [];
        var legend_list = [];
        var newkey = '', newkey_one;
        var string_legend = '';

        if((self.group_field.length) && (this.operator.length <= 1)){
            view_chart = self.orientation == 'horizontal'? 'stackedBarH' : 'stackedBar';
        }else{
            view_chart = self.orientation == 'horizontal'? 'barH' : 'bar';
        }

        _.each(results, function (result) {
            if ((self.group_field.length) && (this.operator.length <= 1)) {
                var legend_key = '';
                _.each(self.group_field, function (res) {
                    result[res] = (typeof result[res] == 'object') ? result[res][1] : result[res];
                    legend_key += result[res];
                });
                newkey = legend_key.replace(/\s+/g,'_').replace(/[^a-zA-Z 0-9]+/g,'_');
                string_legend = legend_key;
            } else {
                newkey = string_legend = "val";
            }

            if (_.contains(group_list, newkey) && _.contains(legend_list, string_legend)) {
                return;
            }
            group_list.push(newkey);
            legend_list.push(string_legend);

            if (this.operator.length > 1) {
                newkey_one = "val1";
                group_list.push(newkey_one);
                legend_list.push(newkey_one);
            }
        }, this);

        if (group_list.length <=1){
            group_list = [];
            legend_list = [];
            newkey = string_legend = "val";
            group_list.push(newkey);
            legend_list.push(string_legend);
        }

        var abscissa_data = {};
        _.each(results, function (result) {
            var label = result[self.chart_info_fields],
              section = {};
            if ((self.group_field.length) && (group_list.length > 1) && (self.operator.length <= 1)){
                var legend_key_two = '';
                _.each(self.group_field, function (res) {
                    result[res] = (typeof result[res] == 'object') ? result[res][1] : result[res];
                    legend_key_two += result[res];
                });
                newkey = legend_key_two.replace(/\s+/g,'_').replace(/[^a-zA-Z 0-9]+/g,'_');
            }else{
                newkey = "val";
            }
            if (abscissa_data[label] == undefined){
                section[self.chart_info_fields] = label;
                _.each(group_list, function (group) {
                    section[group] = 0;
                });
            } else {
                section = abscissa_data[label];
            }
            section[newkey] = result[self.operator_field];
            if (self.operator.length > 1){
                section[newkey_one] = result[self.operator_field_one];
            }
            abscissa_data[label] = section;
        });

        //for legend color
        var grp_color = _.map(legend_list, function (group_legend, index) {
            var legend = {color: COLOR_PALETTE[index]};
            if (group_legend == "val"){
                legend['text'] = self.fields[self.operator_field]['string']
            }else if(group_legend == "val1"){
                legend['text'] = self.fields[self.operator_field_one]['string']
            }else{
                legend['text'] = group_legend;
            }
            return legend;
        });

        //for axis's value and title
        var max,min,step;
        var maximum,minimum;
        if(_.isEmpty(abscissa_data)){
            max = 9;
            min = 0;
            step=1;
        }else{
            var max_min = [];
            _.each(abscissa_data, function (abscissa_datas) {
                _.each(group_list, function(res){
                    max_min.push(abscissa_datas[res]);
                });
            });
            maximum = Math.max.apply(Math,max_min);
            minimum = Math.min.apply(Math,max_min);
            if (maximum == minimum){
                if (maximum == 0){
                    max = 9;
                    min = 0;
                    step=1;
                }else if(maximum > 0){
                    max = maximum + (10 - maximum % 10);
                    min = 0;
                    step = Math.round(max/10);
                }else{
                    max = 0;
                    min = minimum - (10 + minimum % 10);
                    step = Math.round(Math.abs(min)/10);
                }
            }
        }
        var abscissa_description = {
            template: self.chart_info_fields,
            title: "<b>"+self.x_title+"</b>"
        };

        var ordinate_description = {
            lines: true,
            title: "<b>"+self.y_title+"</b>",
            start: min,
            step: step,
            end: max
        };

        var x_axis, y_axis, tooltip;
        if (self.orientation == 'horizontal'){
             x_axis = ordinate_description;
             y_axis = abscissa_description;
        }else{
             x_axis = abscissa_description;
             y_axis = ordinate_description;
        }
        tooltip = self.chart_info_fields;

        var bar_chart = new dhtmlXChart({
            view: view_chart,
            container: self.element_id+"-barchart",
            value:"#"+group_list[0]+"#",
            gradient: "3d",
            border: false,
            width: 1024,
            tooltip:{
                template:"#"+tooltip+"#"+","+grp_color[0]['text']+"="+"#"+group_list[0]+"#"
            },
            radius: 0,
            color:grp_color[0]['color'],
            origin:0,
            xAxis:{
                template:function(obj){
                    if(x_axis['template']){
                        var val = obj[x_axis['template']];
                        val = (typeof val == 'object')?val[1]:(!val?'Undefined':val);
                        if(val.length > 12){
                            val = val.substring(0,12);
                        }
                        return val;
                    }else{
                        return obj;
                    }
                },
                title:x_axis['title'],
                lines:x_axis['lines']
            },
            yAxis:{
                template:function(obj){
                    if(y_axis['template']){
                        var vals = obj[y_axis['template']];
                        vals = (typeof vals == 'object')?vals[1]:(!vals?'Undefined':vals);
                        if(vals.length > 12){
                            vals = vals.substring(0,12);
                        }
                        return vals;
                    }else{
                        return obj;
                    }
                },
                title:y_axis['title'],
                lines: y_axis['lines'],
                start:y_axis['start'],
                step:y_axis['step'],
                end:y_axis['end']
            },
            padding: {
                left: 75
            },
            legend: {
                values: grp_color,
                align:"left",
                valign:"top",
                layout: "x",
                marker:{
                    type:"round",
                    width:12
                }
            }
        });
        for (var m = 1; m<group_list.length;m++){
            bar_chart.addSeries({
                value: "#"+group_list[m]+"#",
                tooltip:{
                    template:"#"+tooltip+"#"+","+grp_color[m]['text']+"="+"#"+group_list[m]+"#"
                },
                color: grp_color[m]['color']
            });
        }
        bar_chart.parse(_.values(abscissa_data), "json");
        jQuery("#"+self.element_id+"-barchart").height(jQuery("#"+self.element_id+"-barchart").height()+50);
        bar_chart.attachEvent("onItemClick", function(id) {
            self.open_list_view(bar_chart.get(id));
        });
    },
    schedule_pie: function(result) {
        var self = this;
        var chart =  new dhtmlXChart({
            view:"pie3D",
            container:self.element_id+"-piechart",
            value:"#"+self.operator_field+"#",
            pieInnerText:function(obj) {
                var sum = chart.sum("#"+self.operator_field+"#");
                var val = obj[self.operator_field] / sum * 100 ;
                return val.toFixed(1) + "%";
            },
            tooltip:{
                template:"#"+self.chart_info_fields+"#"+"="+"#"+self.operator_field+"#"
            },
            gradient:"3d",
            height: 20,
            radius: 200,
            legend: {
                width: 300,
                align:"left",
                valign:"top",
                layout: "x",
                marker:{
                    type:"round",
                    width:12
                },
                template:function(obj){
                    var val = obj[self.chart_info_fields];
                    val = (typeof val == 'object')?val[1]:val;
                    return val;
                }
            }
        });
        chart.parse(result,"json");
        chart.attachEvent("onItemClick", function(id) {
            self.open_list_view(chart.get(id));
        });
    },
    open_list_view : function (id){
        var self = this;
        if($(".dhx_tooltip").is(":visible")) {
            $(".dhx_tooltip").remove('div');
        }
        id = id[this.chart_info_fields];
        if (typeof id == 'object'){
            id = id[0];
        }

        var record_id = "";
        this.dataset.model = this.model;
        if (typeof this.chart_info_fields == 'object'){
            record_id = this.chart_info_fields[0];
        }else{
            record_id = this.chart_info_fields;
        }
        this.dataset.domain = [[record_id, '=', id],['id','in',this.dataset.ids]];
        var modes = !!modes ? modes.split(",") : ["list", "form", "graph"];
        var views = [];
        _.each(modes, function(mode) {
            var view = [false, mode];
            if (self.fields.views && self.fields.views[mode]) {
                view.push(self.fields.views[mode]);
            }
            views.push(view);
        });
        this.do_action({
            "res_model" : this.dataset.model,
            "domain" : this.dataset.domain,
            "views" : views,
            "type" : "ir.actions.act_window",
            "auto_search" : true,
            "view_type" : "list",
            "view_mode" : "list"
        });
    },

    do_search: function(domains, contexts, groupbys) {
        var self = this;
        this.rpc('/web/session/eval_domain_and_context', {
            domains: domains,
            contexts: contexts,
            group_by_seq: groupbys
        }, function (results) {
            // TODO: handle non-empty results.group_by with read_group
            if(results.group_by  && results.group_by != ''){
                self.chart_info_fields = results.group_by[0];
            }else{
                self.chart_info_fields = self.chart_info;
            }
            self.dataset.context = results.context;
            self.dataset.domain = results.domain;
            self.dataset.read_slice([],{}, $.proxy(self, 'load_chart'));
        });
    }
});
// here you may tweak globals object, if any, and play with on_* or do_* callbacks on them
};
// vim:et fdc=0 fdl=0:
