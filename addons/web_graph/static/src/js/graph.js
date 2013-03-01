/*---------------------------------------------------------
 * OpenERP web_graph
 *---------------------------------------------------------*/

openerp.web_graph = function (instance) {

var _lt = instance.web._lt;

// removed ``undefined`` values
var filter_values = function (o) {
    var out = {};
    for (var k in o) {
        if (!o.hasOwnProperty(k) || o[k] === undefined) { continue; }
        out[k] = o[k];
    }
    return out;
};

instance.web.views.add('graph', 'instance.web_graph.GraphView');
instance.web_graph.GraphView = instance.web.View.extend({
    template: "GraphView",
    display_name: _lt('Graph'),
    view_type: "graph",

    init: function(parent, dataset, view_id, options) {
        var self = this;
        this._super(parent);
        this.set_default_options(options);
        this.dataset = dataset;
        this.view_id = view_id;

        this.mode = "bar";          // line, bar, area, pie, radar
        this.orientation = false;    // true: horizontal, false: vertical
        this.stacked = true;

        this.spreadsheet = false;   // Display data grid, allows copy to CSV
        this.forcehtml = false;
        this.legend = "top";        // top, inside, no

        this.domain = [];
        this.context = {};
        this.group_by = [];

        this.graph = null;
    },
    view_loading: function(r) {
        return this.load_graph(r);
    },
    destroy: function () {
        if (this.graph) {
            this.graph.destroy();
        }
        this._super();
    },

    load_graph: function(fields_view_get) {
        // TODO: move  to load_view and document
        var self = this;
        this.fields_view = fields_view_get;
        this.$el.addClass(this.fields_view.arch.attrs['class']);

        this.mode = this.fields_view.arch.attrs.type || 'bar';
        this.orientation = this.fields_view.arch.attrs.orientation == 'horizontal';

        var width = this.$el.parent().width();
        this.$el.css("width", width);
        this.container = this.$el.find("#editor-render-body").css({
            width: width,
            height: Math.min(500, width * 0.8)
        })[0];

        var graph_render = this.proxy('graph_render');
        this.$el.on('click', '.oe_graph_options a', function (evt) {
            var $el = $(evt.target);

            self.graph_render({data: filter_values({
                mode: $el.data('mode'),
                legend: $el.data('legend'),
                orientation: $el.data('orientation'),
                stacked: $el.data('stacked')
            })});
        });

        this.$el.find("#graph_show_data").click(function () {
            self.spreadsheet = ! self.spreadsheet;
            self.graph_render();
        });
        this.$el.find("#graph_switch").click(function () {
            if (self.mode != 'radar') {
                self.orientation = ! self.orientation;
            }
            self.graph_render();
        });

        this.$el.find("#graph_download").click(function () {
            if (self.legend == "top") { self.legend = "inside"; }
            self.forcehtml = true;

            self.graph_get_data().done(function (result) {
                self.graph_render_all(result).download.saveImage('png');
            }).always(function () {
                self.forcehtml = false;
            });
        });
        this.trigger('graph_view_loaded', fields_view_get);
    },

    get_format: function (options) {
        options = options || {};
        var legend = {
            show: this.legend != 'no',
        };

        switch (this.legend) {
        case 'top':
            legend.noColumns = 4;
            legend.container = this.$el.find("div.graph_header_legend")[0];
            break;
        case 'inside':
            legend.position = 'nw';
            legend.backgroundColor = '#D2E8FF';
            break;
        }

        return _.extend({
            legend: legend,
            mouse: {
                track: true,
                relative: true
            },
            spreadsheet : {
                show: this.spreadsheet,
                initialTab: "data"
            },
            HtmlText : (options.xaxis && options.xaxis.labelsAngle) ? false : !this.forcehtml,
        }, options);
    },

    make_graph: function (mode, container, data) {
        if (mode === 'area') { mode = 'line'; }
        var format = this.get_format(this['options_' + mode](data));
        return Flotr.draw(container, data.data, format);
    },

    options_bar: function (data) {
        var min = _(data.data).chain()
            .map(function (record) {
                if (record.data.length > 0){
	                return _.min(record.data, function (item) {
	                    return item[1];
	                })[1];
                }
            }).min().value();
        return {
            bars : {
                show : true,
                stacked : this.stacked,
                horizontal : this.orientation,
                barWidth : 0.7,
                lineWidth : 1
            },
            grid : {
                verticalLines : this.orientation,
                horizontalLines : !this.orientation,
                outline : "sw",
            },
            yaxis : {
                ticks: this.orientation ? data.ticks : false,
                min: !this.orientation ? (min < 0 ? min : 0) : null
            },
            xaxis : {
                labelsAngle: 45,
                ticks: this.orientation ? false : data.ticks,
                min: this.orientation ? (min < 0 ? min : 0) : null
            }
        };
    },

    options_pie: function (data) {
        return {
            pie : {
                show: true
            },
            grid : {
                verticalLines : false,
                horizontalLines : false,
                outline : "",
            },
            xaxis :  {showLabels: false},
            yaxis :  {showLabels: false},
        };
    },

    options_radar: function (data) {
        return {
            radar : {
                show : true,
                stacked : this.stacked
            },
            grid : {
                circular : true,
                minorHorizontalLines : true
            },
            xaxis : {
                ticks: data.ticks
            },
        };
    },

    options_line: function (data) {
        return {
            lines : {
                show : true,
            },
            points: {
                show: true,
            },
            grid : {
                verticalLines : this.orientation,
                horizontalLines : !this.orientation,
                outline : "sw",
            },
            yaxis : {
                ticks: this.orientation ? data.ticks : false
            },
            xaxis : {
                labelsAngle: 45,
                ticks: this.orientation ? false : data.ticks
            }
        };
    },

    graph_get_data: function () {
        var model = this.dataset.model,
            domain = new instance.web.CompoundDomain(this.domain || []),
            context = new instance.web.CompoundContext(this.context || {}),
            group_by = this.group_by || [],
            view_id = this.view_id  || false,
            mode = this.mode || 'bar',
            orientation = this.orientation || false,
            stacked = this.stacked || false;

        var obj = new instance.web.Model(model);
        var view_get;
        var fields;
        var result = [];
        var ticks = {};

        return this.alive(obj.call("fields_view_get", [view_id, 'graph', context]).then(function(tmp) {
            view_get = tmp;
            fields = view_get['fields'];
            var toload = _.select(group_by, function(x) { return fields[x] === undefined });
            if (toload.length >= 1)
                return obj.call("fields_get", [toload, context]);
            else
                return $.when([]);
        }).then(function (fields_to_add) {
            _.extend(fields, fields_to_add);

            var tree = $($.parseXML(view_get['arch']));
            
            var pos = 0;
            var xaxis = _.clone(group_by || []);
            var yaxis = [];
            tree.find("field").each(function() {
                var field = $(this);
                if (! field.attr("name"))
                    return;
                if ((group_by.length == 0) && ((! pos) || instance.web.py_eval(field.attr('group') || "false"))) {
                    xaxis.push(field.attr('name'));
                }
                if (pos && ! instance.web.py_eval(field.attr('group') || "false")) {
                    yaxis.push(field.attr('name'));
                }
                pos += 1;
            });

            if (xaxis.length === 0)
                throw new Error("No field for the X axis!");
            if (yaxis.length === 0)
                throw new Error("No field for the Y axis!");

            // Convert a field's data into a displayable string

            function _convert_key(field, data) {
                if (fields[field]['type'] === 'many2one')
                    data = data && data[0];
                return data;
            }

            function _convert(field, data, tick) {
                tick = tick === undefined ? true : false;
                try {
                    data = instance.web.format_value(data, fields[field]);
                } catch(e) {
                    data = "" + data;
                }
                if (tick) {
                    if (ticks[data] === undefined)
                        ticks[data] = _.size(ticks);
                    return ticks[data];
                }
                return data || 0;
            }

            function _orientation(x, y) {
                if (! orientation)
                    return [x, y]
                return [y, x]
            }

            if (mode === "pie") {
                return obj.call("read_group", [domain, yaxis.concat([xaxis[0]]), [xaxis[0]]], {context: context}).then(function(res) {
                    _.each(res, function(record) {
                        result.push({
                            'data': [[_convert(xaxis[0], record[xaxis[0]]), record[yaxis[0]]]],
                            'label': _convert(xaxis[0], record[xaxis[0]], false)
                        });
                    });
                });
            } else if ((! stacked) || (xaxis.length < 2)) {
                var defs = [];
                _.each(xaxis, function(x) {
                    defs.push(obj.call("read_group", [domain, yaxis.concat([x]), [x]], {context: context}).then(function(res) {
                        return [x, res];
                    }));
                });
                return $.when.apply($, defs).then(function() {
                    _.each(_.toArray(arguments), function(res) {
                        var x = res[0];
                        res = res[1];
                        result.push({
                            'data': _.map(res, function(record) {
                                return _orientation(_convert(x, record[x]), record[yaxis[0]] || 0);
                            }),
                            'label': fields[x]['string']
                        });
                    });
                });
            } else {
                xaxis.reverse();
                return obj.call("read_group", [domain, yaxis.concat(xaxis.slice(0, 1)), xaxis.slice(0, 1)], {context: context}).then(function(axis) {
                    var defs = [];
                    _.each(axis, function(x) {
                        var key = x[xaxis[0]]
                        defs.push(obj.call("read_group", [domain, yaxis.concat(xaxis.slice(1, 2)), xaxis.slice(1, 2)], {context: context}).then(function(res) {
                            return [x, key, res];
                        }));
                    });
                    return $.when.apply($, defs).then(function() {
                        _.each(_.toArray(arguments), function(res) {
                            var x = res[0];
                            var key = res[1];
                            res = res[2];
                            result.push({
                                'data': _.map(res, function(record) {
                                    return _orientation(_convert(xaxis[1], record[xaxis[1]]), record[yaxis[0]] || 0);
                                }),
                                'label': _convert(xaxis[0], key, false)
                            })
                        });
                    });
                });
            }
        }).then(function() {
            var res = {
                'data': result,
                'ticks': _.map(ticks, function(el, key) { return [el, key] })
            };
            return res;
        }));
    },

    // Render the graph and update menu styles
    graph_render: function (options) {
        options = options || {};
        _.extend(this, options.data);

        return this.graph_get_data()
            .done(this.proxy('graph_render_all'));
    },

    graph_render_all: function (data) {
        var i;
        if (this.mode=='area') {
            for (i=0; i<data.data.length; i++) {
                data.data[i].lines = {fill: true}
            }
        }
        if (this.graph) {
            this.graph.destroy();
        }

        // Render the graph
        this.$el.find(".graph_header_legend").children().remove();
        this.graph = this.make_graph(this.mode, this.container, data);

        // Update styles of menus

        this.$el.find("a").removeClass("active");

        var $active = this.$el.find('a[data-mode=' + this.mode + ']');
        if ($active.length > 1) {
            $active = $active.filter('[data-stacked=' + this.stacked + ']');
        }
        $active = $active.add(
            this.$el.find('a:not([data-mode])[data-legend=' + this.legend + ']'));

        $active.addClass('active');

        if (this.spreadsheet) {
            this.$el.find("#graph_show_data").addClass("active");
        }
        return this.graph;
    },

    // render the graph using the domain, context and group_by
    // calls the 'graph_data_get' python controller to process all data
    // TODO: check is group_by should better be in the context
    do_search: function(domain, context, group_by) {
        this.domain = domain;
        this.context = context;
        this.group_by = group_by;

        this.graph_render();
    },

    do_show: function() {
        this.do_push_state({});
        return this._super();
    },
});
};
