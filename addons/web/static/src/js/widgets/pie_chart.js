odoo.define('web.PieChart', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var widgetRegistry = require('web.widget_registry');

var QWeb = core.qweb;



var PieChart = Widget.extend({
    template: 'web.PieChart',
    events: {
    },

    /**
     * override
     *
     * @param {Widget} parent
     * @param {Object} record

     * @param {Object} items list of menu items (type IGMenuItem below)
     *   interface IMenuItem {
     *      itemId: string; (optional) unique id associated with the item
     *      description: string; label printed on screen
     *      groupId: string;
     *      isActive: boolean; (optional) determines if the item is considered active
     *      isOpen: boolean; (optional) in case there are options the submenu presenting the options
     *                                is opethis._rpc({
    model: 'some.model',
    method: 'some_method',
    args: [some, args],
});ned or closed according to isOpen
     *      isRemovable: boolean; (optional) can be removed from menu
     *      options: array of objects with 'optionId' and 'description' keys; (optional)
     *      currentOptionId: string refers to an optionId that is activated if item is active (optional)
     *   }
     */
    init: function (parent, record, node) {
        this._super(parent);
        
        this.record = record;
        this.model = record.model;
        this.measure = node.attrs.measure;
        this.groupby = node.attrs.groupby;
    },
    /**
     * override
     */
    willStart: function () {
        var self = this;
        this.data = [];

        var query = {
            model: this.model,
            method: 'read_group',
            domain: [],
            fields: [this.measure],
            groupBy: [this.groupby],
            lazy: false,
        };

        return this._rpc(query).then(function(result) {
            for (var i in result) {
                self.data.push({
                    "label": result[i][self.groupby][1],
                    "value": result[i][self.measure],
                });
            }
        });       
    },
    /**
     * override
     */
    start: function () {
        var self = this;
        var svg = d3.select(this.$el[0]).append('svg');

        nv.addGraph(function() {
            var chart = nv.models.pieChart()
                                 .x(function(d) { return d.label })
                                 .y(function(d) { return d.value })
                                 .showLabels(true);

            svg.datum(self.data)
               .transition().duration(0)
               .call(chart);

            return chart;
        });
        return this._super.apply(this, arguments);

        // return $.when(); //  A vérfier
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

   
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

  
  
});

widgetRegistry.add('pie_chart', PieChart);

return PieChart;

});
