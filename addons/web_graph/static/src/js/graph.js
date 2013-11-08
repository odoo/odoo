/*---------------------------------------------------------
 * OpenERP web_graph
 *---------------------------------------------------------*/
/*global openerp:true*/
/*global $:true*/
'use strict';

openerp.web_graph = function (instance) {

var _lt = instance.web._lt;
var _t = instance.web._t;

instance.web.views.add('graph', 'instance.web_graph.GraphView');

instance.web_graph.GraphView = instance.web.View.extend({
    template: 'GraphView',
    display_name: _lt('Graph'),
    view_type: 'graph',
    events: {
        'click .graph_mode_selection li' : function (event) {
            event.preventDefault();
            var mode = event.target.attributes['data-mode'].nodeValue;
            if (mode == 'data') {
                this.chart_view.hide();
                this.pivot_table.show();
            } else {
                this.pivot_table.hide();
                this.chart_view.show(mode);
            }
        },
    },

    init: function(parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, options);
        this.pivot_table = new PivotTable(this);
        this.chart_view = new ChartView(this);
    },

    view_loading: function (fields_view_get) {
        this.pivot_table.appendTo('.graph_pivot');
        this.chart_view.appendTo('.graph_chart');
        this.chart_view.hide();
    },

    do_show: function () {
        this.do_push_state({});
        return this._super();
    },
});

var PivotTable = instance.web.Widget.extend({
    template: 'pivot_table',

    show: function () {
        this.$el.css('display', 'block');
    },

    hide: function () {
        this.$el.css('display', 'none');
    },

});

var ChartView = instance.web.Widget.extend({
    template: 'chart_view',

    show: function () {
        this.$el.css('display', 'block');
    },

    hide: function () {
        this.$el.css('display', 'none');
    },

});



};
