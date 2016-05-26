/*---------------------------------------------------------
 * Odoo Graph view
 *---------------------------------------------------------*/

(function () {
'use strict';

var instance = openerp,
    _lt = instance.web._lt,
    _t = instance.web._t,
    QWeb = instance.web.qweb;

nv.dev = false;  // sets nvd3 library in production mode

instance.web.views.add('graph', 'instance.web.GraphView');

instance.web.GraphView = instance.web.View.extend({
    className: 'oe_graph',
    display_name: _lt('Graph'),
    view_type: 'graph',

    init: function(parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, options);

        this.model = new instance.web.Model(dataset.model, {group_by_no_leaf: true});
        this.measures = [];
        this.active_measure = '__count__';
        this.initial_groupbys = [];
        this.widget = undefined;
    },
    start: function () {
        var load_fields = this.model.call('fields_get', [], {context: this.dataset.get_context()})
                .then(this.prepare_fields.bind(this));

        return $.when(this._super(), load_fields).then(this.render_buttons.bind(this));
    },
    render_buttons: function () {
        var context = {measures: _.pairs(_.omit(this.measures, '__count__'))};
        this.$buttons.html(QWeb.render('GraphView.buttons', context));
        this.$measure_list = this.$buttons.find('.oe-measure-list');
        this.update_measure();
        this.$buttons.find('button').tooltip();
        this.$buttons.click(this.on_button_click.bind(this));
    },
    update_measure: function () {
        var self = this;
        this.$measure_list.find('li').each(function (index, li) {
            $(li).toggleClass('selected', $(li).data('field') === self.active_measure);
        });
    },
    view_loading: function (fvg) {
        var self = this;
        fvg.arch.children.forEach(function (field) {
            var name = field.attrs.name;
            if (field.attrs.interval) {
                name += ':' + field.attrs.interval;
            }
            if (field.attrs.type === 'measure') {
                self.active_measure = name;
            } else {
                self.initial_groupbys.push(name);
            }
        });
        this.active_mode = fvg.arch.attrs.type || 'bar';
    },
    do_show: function () {
        this.do_push_state({});
        this.$el.show();
        return this._super();
    },
    prepare_fields: function (fields) {
        var self = this;
        this.fields = fields;
        _.each(fields, function (field, name) {
            if ((name !== 'id') && (field.store === true)) {
                if (field.type === 'integer' || field.type === 'float') {
                    self.measures[name] = field;
                }
            }
        });
        this.measures.__count__ = {string: _t("Quantity"), type: "integer"};
    },
    do_search: function (domain, context, group_by) {
        if (!this.widget) {
            this.initial_groupbys = context.graph_groupbys || this.initial_groupbys;
            this.widget = new instance.web.GraphWidget(this, this.dataset.model, {
                measure: context.graph_measure || this.active_measure,
                mode: context.graph_mode || this.active_mode,
                domain: domain,
                groupbys: this.initial_groupbys,
                context: context,
                fields: this.fields,
            });
            // append widget
            this.$el.hide();
            this.widget.appendTo(this.$el);
        } else {
            var groupbys = group_by.length ? group_by : this.initial_groupbys.slice(0);
            this.widget.update_data(domain, groupbys);
        }
    },
    get_context: function () {
        return !this.widget ? {} : {
            graph_mode: this.widget.mode,
            graph_measure: this.widget.measure,
            graph_groupbys: this.widget.groupbys
        };
    },
    on_button_click: function (event) {
        var $target = $(event.target);
        if ($target.hasClass('oe-bar-mode')) {this.widget.set_mode('bar');}
        if ($target.hasClass('oe-line-mode')) {this.widget.set_mode('line');}
        if ($target.hasClass('oe-pie-mode')) {this.widget.set_mode('pie');}
        if ($target.parents('.oe-measure-list').length) {
            var parent = $target.parent(),
                field = parent.data('field');
            this.active_measure = field;
            parent.toggleClass('selected');
            event.stopPropagation();
            this.update_measure();
            this.widget.set_measure(this.active_measure);
        }
    },
});

instance.web.GraphWidget = instance.web.Widget.extend({
    init: function (parent, model, options) {
        this._super(parent);
        this.context = options.context;
        this.fields = options.fields;
        this.fields.__count__ = {string: _t("Quantity"), type: "integer"};
        this.model = new instance.web.Model(model, {group_by_no_leaf: true});

        this.domain = options.domain || [];
        this.groupbys = options.groupbys || [];
        this.mode = options.mode || "bar";
        this.measure = options.measure || "__count__";
    },
    start: function () {
        return this.load_data().then(this.proxy('display_graph'));
    },
    update_data: function (domain, groupbys) {
        this.domain = domain;
        this.groupbys = groupbys;
        return this.load_data().then(this.proxy('display_graph'));
    },
    set_mode: function (mode) {
        this.mode = mode;
        this.display_graph();
    },
    set_measure: function (measure) {
        this.measure = measure;
        return this.load_data().then(this.proxy('display_graph'));        
    },
    load_data: function () {
        var fields = this.groupbys.slice(0);
        if (this.measure !== '__count__'.slice(0))
            fields = fields.concat(this.measure);
        return this.model
                    .query(fields)
                    .filter(this.domain)
                    .context(this.context)
                    .lazy(false)
                    .group_by(this.groupbys.slice(0,2))
                    .then(this.proxy('prepare_data'));
    },
    prepare_data: function () {
        var raw_data = arguments[0],
            is_count = this.measure === '__count__';
        var data_pt, j, values, value;

        this.data = [];
        for (var i = 0; i < raw_data.length; i++) {
            data_pt = raw_data[i].attributes;
            values = [];
            if (this.groupbys.length === 1) data_pt.value = [data_pt.value];
            for (j = 0; j < data_pt.value.length; j++) {
                values[j] = this.sanitize_value(data_pt.value[j], data_pt.grouped_on[j]);
            }
            value = is_count ? data_pt.length : data_pt.aggregates[this.measure];
            this.data.push({
                labels: values,
                value: value
            });
        }
    },
    sanitize_value: function (value, field) {
        if (value === false) return _t("Undefined");
        if (value instanceof Array) return value[1];
        if (field && this.fields[field] && (this.fields[field].type === 'selection')) {
            var selected = _.where(this.fields[field].selection, {0: value})[0];
            return selected ? selected[1] : value;
        }
        return value;
    },
    display_graph: function () {
        if (this.to_remove) {
            nv.utils.offWindowResize(this.to_remove);
        }
        this.$el.empty();
        if (!this.data.length) {
            this.$el.append(QWeb.render('GraphView.error', {
                title: _t("No data to display"),
                description: _t("No data available for this chart.  " +
                    "Try to add some records, or make sure that" +
                    "there is no active filter in the search bar."),
            }));
        } else {
            this['display_' + this.mode]();
        }
    },
    display_bar: function () {
        // prepare data for bar chart
        var data, values,
            measure = this.fields[this.measure].string;

        // zero groupbys
        if (this.groupbys.length === 0) {
            data = [{
                values: [{
                    x: measure,
                    y: this.data[0].value}],
                key: measure
            }];
        } 
        // one groupby
        if (this.groupbys.length === 1) {
            values = this.data.map(function (datapt) {
                return {x: datapt.labels, y: datapt.value};
            });
            data = [
                {
                    values: values,
                    key: measure,
                }
            ];
        }
        if (this.groupbys.length > 1) {
            var xlabels = [],
                series = [],
                label, serie, value;
            values = {};
            for (var i = 0; i < this.data.length; i++) {
                label = this.data[i].labels[0];
                serie = this.data[i].labels[1];
                value = this.data[i].value;
                if ((!xlabels.length) || (xlabels[xlabels.length-1] !== label)) {
                    xlabels.push(label);
                }
                series.push(this.data[i].labels[1]);
                if (!(serie in values)) {values[serie] = {};}
                values[serie][label] = this.data[i].value;
            }
            series = _.uniq(series);
            data = [];
            var current_serie, j;
            for (i = 0; i < series.length; i++) {
                current_serie = {values: [], key: series[i]};
                for (j = 0; j < xlabels.length; j++) {
                    current_serie.values.push({
                        x: xlabels[j],
                        y: values[series[i]][xlabels[j]] || 0,
                    });
                }
                data.push(current_serie);
            }
        }
        var svg = d3.select(this.$el[0]).append('svg');
        svg.datum(data);

        svg.transition().duration(0);

        var chart = nv.models.multiBarChart();
        var maxVal = _.max(values, function(v) {return v.y})
        chart.options({
          margin: {left: 12 * String(maxVal && maxVal.y || 10000000).length},
          delay: 250,
          transitionDuration: 10,
          showLegend: true,
          showXAxis: true,
          showYAxis: true,
          rightAlignYAxis: false,
          stacked: true,
          reduceXTicks: false,
          // rotateLabels: 40,
          showControls: (this.groupbys.length > 1)
        });
        chart.yAxis.tickFormat(function(d) { return openerp.web.format_value(d, { type : 'float' });});

        chart(svg);
        this.to_remove = chart.update;
        nv.utils.onWindowResize(chart.update);
    },
    display_pie: function () {
        var data = [],
            tickValues,
            tickFormat,
            measure = this.fields[this.measure].string;

        var all_negative = true,
            some_negative = false,
            all_zero = true;
        this.data.forEach(function (datapt) {
            all_negative = all_negative && (datapt.value < 0);
            some_negative = some_negative || (datapt.value < 0);
            all_zero = all_zero && (datapt.value === 0)
        });
        if (some_negative && !all_negative) {
            return this.$el.append(QWeb.render('GraphView.error', {
                title: _t("Invalid data"),
                description: _t("Pie chart cannot mix positive and negative numbers. " +
                    "Try to change your domain to only display positive results"),
            }));
        }
        if (all_zero) {
            return this.$el.append(QWeb.render('GraphView.error', {
                title: _t("Invalid data"),
                description: _t("Pie chart cannot display all zero numbers.. " +
                    "Try to change your domain to display positive results"),
            }));
        }
        if (this.groupbys.length) {
            data = this.data.map(function (datapt) {
                return {x:datapt.labels.join("/"), y: datapt.value};
            });
        }
        var svg = d3.select(this.$el[0]).append('svg');
        svg.datum(data);

        svg.transition().duration(100);

        var chart = nv.models.pieChart();
        chart.options({
          delay: 250,
          transitionDuration: 100,
          color: d3.scale.category10().range(),
        });

        chart(svg);
        this.to_remove = chart.update;
        nv.utils.onWindowResize(chart.update);
    },
    display_line: function () {
        if (this.data.length < 2) {
            this.$el.append(QWeb.render('GraphView.error', {
                title: _t("Not enough data points"),
                description: "You need at least two data points to display a line chart."
            }));
            return;
        }
        var self = this,
            data = [],
            tickValues,
            tickFormat,
            measure = this.fields[this.measure].string;
        if (this.groupbys.length === 1) {
            var values = this.data.map(function (datapt, index) {
                return {x: index, y: datapt.value};
            });
            data = [
                {
                    values: values,
                    key: measure,
                }
            ];
            tickValues = this.data.map(function (d, i) { return i;});
            tickFormat = function (d) {return self.data[d].labels;};
        }
        if (this.groupbys.length > 1) {
            data = [];
            var data_dict = {},
                tick = 0,
                tickLabels = [],
                serie, tickLabel,
                identity = function (p) {return p;};
            tickValues = [];
            for (var i = 0; i < this.data.length; i++) {
                if (this.data[i].labels[0] !== tickLabel) {
                    tickLabel = this.data[i].labels[0];
                    tickValues.push(tick);
                    tickLabels.push(tickLabel);
                    tick++;
                }
                serie = this.data[i].labels[1];
                if (!data_dict[serie]) {
                    data_dict[serie] = {
                        values: [],
                        key: serie,
                    };
                }
                data_dict[serie].values.push({
                    x: tick, y: this.data[i].value,
                });
                data = _.map(data_dict, identity);
            }
            tickFormat = function (d) {return tickLabels[d];};
        }

        var svg = d3.select(this.$el[0]).append('svg');
        svg.datum(data);

        svg.transition().duration(0);

        var chart = nv.models.lineChart();
        var maxVal = _.max(values, function(v) {return v.y})
        chart.options({
          margin: {left: 12 * String(maxVal && maxVal.y || 10000000).length, right: 50},
          useInteractiveGuideline: true,
          showLegend: true,
          showXAxis: true,
          showYAxis: true,
        });
        chart.xAxis.tickValues(tickValues)
            .tickFormat(tickFormat);

        chart(svg);
        this.to_remove = chart.update;
        nv.utils.onWindowResize(chart.update);  
    },
    destroy: function () {
        nv.utils.offWindowResize(this.to_remove);
        return this._super();
    }
});

// monkey patch nvd3 to allow removing eventhandler on windowresize events
// see https://github.com/novus/nvd3/pull/396 for more details

// Adds a resize listener to the window.
nv.utils.onWindowResize = function(fun) {
    if (fun === null) return;
    window.addEventListener('resize', fun);
};

// Backwards compatibility with current API.
nv.utils.windowResize = nv.utils.onWindowResize;

// Removes a resize listener from the window.
nv.utils.offWindowResize = function(fun) {
    if (fun === null) return;
    window.removeEventListener('resize', fun);
};

// monkey patch nvd3 to prevent crashes when user changes view and nvd3 tries
// to remove tooltips after 500 ms...  seriously nvd3, what were you thinking?
nv.tooltip.cleanup = function () {
    $('.nvtooltip').remove();
};


})();
