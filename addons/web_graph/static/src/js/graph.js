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

    init: function(parent, dataset, view_id, options) {
        this._super(parent);
        this.set_default_options(options);
        this.dataset = dataset;
        this.view_id = view_id;

        this.first_field = null;
        this.abscissa = null;
        this.ordinate = null;
        this.columns = [];
        this.group_field = null;
    },
    do_show: function () {
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    },
    start: function() {
        var self = this;
        this._super();
        var loaded;
        if (this.embedded_view) {
            loaded = $.when([self.embedded_view]);
        } else {
            loaded = this.rpc('/web/view/load', {
                    model: this.dataset.model,
                    view_id: this.view_id,
                    view_type: 'graph'
            });
        }
        return $.when(
            this.dataset.call('fields_get', []),
            loaded)
            .then(function (fields_result, view_result) {
                self.fields = fields_result[0];
                self.fields_view = view_result[0];
                self.on_loaded();
            });
    },
    /**
     * Returns all object fields involved in the graph view
     */
    list_fields: function () {
        var fs = [this.abscissa];
        fs.push.apply(fs, _(this.columns).pluck('name'));
        if (this.group_field) {
            fs.push(this.group_field);
        }
        return fs;
    },
    on_loaded: function() {
        this.chart = this.fields_view.arch.attrs.type || 'pie';
        this.orientation = this.fields_view.arch.attrs.orientation || 'vertical';

        _.each(this.fields_view.arch.children, function (field) {
            var attrs = field.attrs;
            if (attrs.group) {
                this.group_field = attrs.name;
            } else if(!this.abscissa) {
                this.first_field = this.abscissa = attrs.name;
            } else {
                this.columns.push({
                    name: attrs.name,
                    operator: attrs.operator || '+'
                });
            }
        }, this);
        this.ordinate = this.columns[0].name;
    },
    schedule_chart: function(results) {
        var self = this;
        this.$element.html(QWeb.render("GraphView", {
            "fields_view": this.fields_view,
            "chart": this.chart,
            'element_id': this.element_id
        }));

        var fields = _(this.columns).pluck('name').concat([this.abscissa]);
        if (this.group_field) { fields.push(this.group_field); }
        // transform search result into usable records (convert from OpenERP
        // value shapes to usable atomic types
        var records = _(results).map(function (result) {
            var point = {};
            _(result).each(function (value, field) {
                if (!_(fields).contains(field)) { return; }
                if (value === false) { point[field] = false; return; }
                switch (self.fields[field].type) {
                case 'selection':
                    point[field] = _(self.fields[field].selection).detect(function (choice) {
                        return choice[0] === value;
                    })[1];
                    break;
                case 'many2one':
                    point[field] = value[1];
                    break;
                case 'integer': case 'float': case 'char':
                case 'date': case 'datetime':
                    point[field] = value;
                    break;
                default:
                    throw new Error(
                        "Unknown field type " + self.fields[field].type
                        + "for field " + field + " (" + value + ")");
                }
            });
            return point;
        });
        // aggregate data, because dhtmlx is crap. Aggregate on abscissa field,
        // leave split on group field => max m*n records where m is the # of
        // values for the abscissa and n is the # of values for the group field
        var graph_data = [];
        _(records).each(function (record) {
            var abscissa = record[self.abscissa],
                group = record[self.group_field];
            var r = _(graph_data).detect(function (potential) {
                return potential[self.abscissa] === abscissa
                        && (!self.group_field
                            || potential[self.group_field] === group);
            });
            var datapoint = r || {};

            datapoint[self.abscissa] = abscissa;
            if (self.group_field) { datapoint[self.group_field] = group; }
            _(self.columns).each(function (column) {
                var val = record[column.name],
                    aggregate = datapoint[column.name];
                switch(column.operator) {
                case '+':
                    datapoint[column.name] = (aggregate || 0) + val;
                    return;
                case '*':
                    datapoint[column.name] = (aggregate || 1) * val;
                    return;
                case 'min':
                    datapoint[column.name] = (aggregate || Infinity) > val
                                           ? val
                                           : aggregate;
                    return;
                case 'max':
                    datapoint[column.name] = (aggregate || -Infinity) < val
                                           ? val
                                           : aggregate;
                }
            });

            if (!r) { graph_data.push(datapoint); }
        });
        graph_data = _(graph_data).sortBy(function (point) {
            return point[self.abscissa] + '[[--]]' + point[self.group_field];
        });

        if (this.chart == 'bar') {
            return this.schedule_bar(graph_data);
        } else if (this.chart == "pie") {
            return this.schedule_pie(graph_data);
        }
    },

    schedule_bar: function(results) {
        var self = this;

        var group_list, view_chart;
        if (!this.group_field) {
            view_chart = (this.orientation === 'horizontal') ? 'barH' : 'bar';
            group_list = _(this.columns).map(function (column, index) {
                return {
                    group: column.name,
                    text: self.fields[column.name].string,
                    color: COLOR_PALETTE[index % (COLOR_PALETTE.length)]
                }
            });
        } else {
            // dhtmlx handles clustered bar charts (> 1 column per abscissa
            // value) and stacked bar charts (basically the same but with the
            // columns on top of one another instead of side by side), but it
            // does not handle clustered stacked bar charts
            if (this.columns.length > 1) {
                this.$element.text(
                    'OpenERP Web does not support combining grouping and '
                  + 'multiple columns in graph at this time.');
                throw new Error(
                    'dhtmlx can not handle columns counts of that magnitude');
            }
            // transform series for clustered charts into series for stacked
            // charts
            view_chart = (this.orientation === 'horizontal')
                    ? 'stackedBarH' : 'stackedBar';
            group_list = _(results).chain()
                    .pluck(this.group_field)
                    .uniq()
                    .map(function (value, index) {
                        return {
                            group: self.ordinate + '_' +
                                    value.toLowerCase().replace(/\s/g, '_'),
                            text: value,
                            color: COLOR_PALETTE[index % COLOR_PALETTE.length]
                        };
                    }).value();

            results = _(results).chain()
                .groupBy(function (record) { return record[self.abscissa]; })
                .map(function (records) {
                    var r = {};
                    // second argument is coerced to a str, no good for boolean
                    r[self.abscissa] = records[0][self.abscissa];
                    _(records).each(function (record) {
                        var key = _.sprintf('%s_%s',
                            self.ordinate,
                            record[self.group_field].toLowerCase().replace(/\s/g, '_'));
                        r[key] = record[self.ordinate];
                    });
                    return r;
                })
                .value();
        }

        var abscissa_description = {
            title: "<b>" + this.fields[this.abscissa].string + "</b>",
            template: function (obj) {
                return obj[self.abscissa] || 'Undefined';
            }
        };

        var ordinate_description = {
            lines: true,
            title: "<b>" + this.fields[this.ordinate].string + "</b>"
        };

        var x_axis, y_axis;
        if (self.orientation == 'horizontal') {
            x_axis = ordinate_description;
            y_axis = abscissa_description;
        } else {
            x_axis = abscissa_description;
            y_axis = ordinate_description;
        }
        
        var bar_chart = new dhtmlXChart({
            view: view_chart,
            container: this.element_id+"-barchart",
            value:"#"+group_list[0].group+"#",
            gradient: "3d",
            border: false,
            width: 1024,
            tooltip:{
                template: _.sprintf("#%s#, %s=#%s#",
                    this.abscissa, group_list[0].text, group_list[0].group)
            },
            radius: 0,
            color:group_list[0].color,
            origin:0,
            xAxis: x_axis,
            yAxis: y_axis,
            padding: {
                left: 75
            },
            legend: {
                values: group_list,
                align:"left",
                valign:"top",
                layout: "x",
                marker: {
                    type:"round",
                    width:12
                }
            }
        });
        for (var m = 1; m<group_list.length;m++){
            var column = group_list[m];
            if (column.group === this.group_field) { continue; }
            bar_chart.addSeries({
                value: "#"+column.group+"#",
                tooltip:{
                    template: _.sprintf("#%s#, %s=#%s#",
                        this.abscissa, column.text, column.group)
                },
                color: column.color
            });
        }
        bar_chart.parse(results, "json");
        jQuery("#"+this.element_id+"-barchart").height(jQuery("#"+this.element_id+"-barchart").height()+50);
        bar_chart.attachEvent("onItemClick", function(id) {
            self.open_list_view(bar_chart.get(id));
        });
    },
    schedule_pie: function(result) {
        var self = this;
        var chart =  new dhtmlXChart({
            view:"pie3D",
            container:self.element_id+"-piechart",
            value:"#"+self.ordinate+"#",
            pieInnerText:function(obj) {
                var sum = chart.sum("#"+self.ordinate+"#");
                var val = obj[self.ordinate] / sum * 100 ;
                return val.toFixed(1) + "%";
            },
            tooltip:{
                template:"#"+self.abscissa+"#"+"="+"#"+self.ordinate+"#"
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
                    return obj[self.abscissa] || 'Undefined';
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
        id = id[this.abscissa];
        if (typeof id == 'object'){
            id = id[0];
        }

        var record_id = this.abscissa;
        var modes = ["list", "form", "graph"];
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
            "domain" : [[record_id, '=', id], ['id','in',this.dataset.ids]],
            "views" : views,
            "type" : "ir.actions.act_window",
            "auto_search" : true,
            "view_type" : "list",
            "view_mode" : "list"
        });
    },

    do_search: function(domain, context, group_by) {
        // TODO: handle non-empty group_by with read_group?
        if (!_(group_by).isEmpty()) {
            this.abscissa = group_by[0];
        } else {
            this.abscissa = this.first_field;
        }
        this.dataset.read_slice(this.list_fields(), {}, $.proxy(this, 'schedule_chart'));
    }
});
};
// vim:et fdc=0 fdl=0:
