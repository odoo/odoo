odoo.define('web.PieChart', function (require) {
"use strict";

/**
 * This widget render a Pie Chart. It is used in the dashboard view.
 */

var core = require('web.core');
var Domain = require('web.Domain');
var viewRegistry = require('web.view_registry');
var Widget = require('web.Widget');
var widgetRegistry = require('web.widget_registry');
const { loadLegacyViews } = require("@web/legacy/legacy_views");

var qweb = core.qweb;

var PieChart = Widget.extend({
    className: 'o_pie_chart',

    /**
     * @override
     * @param {Widget} parent
     * @param {Object} record
     * @param {Object} node node from arch
     */
    init: function (parent, record, node) {
        this._super.apply(this, arguments);

        var modifiers = node.attrs.modifiers;
        var domain = record.domain.concat(
            Domain.prototype.stringToArray(modifiers.domain || '[]'));
        var arch = qweb.render('web.LegacyPieChart', {
            modifiers: modifiers,
            title: node.attrs.title || modifiers.title || modifiers.measure,
        });

        var pieChartContext = JSON.parse(JSON.stringify(record.context));
        delete pieChartContext.graph_mode;
        delete pieChartContext.graph_measure;
        delete pieChartContext.graph_groupbys;

        this.subViewParams = {
            modelName: record.model,
            withButtons: false,
            withControlPanel: false,
            withSearchPanel: false,
            isEmbedded: true,
            useSampleModel: record.isSample,
            mode: 'pie',
        };
        this.subViewParams.searchQuery = {
            context: pieChartContext,
            domain: domain,
            groupBy: [],
            timeRanges: record.timeRanges || {},
        };

        this.viewInfo = {
            arch: arch,
            fields: record.fields,
            viewFields: record.fieldsInfo.dashboard,
        };
    },
    /**
     * Instantiates the pie chart view and starts the graph controller.
     *
     * @override
     */
    willStart: async function () {
        var self = this;
        const _super = this._super.bind(this, ...arguments);
        await loadLegacyViews();
        var def1 = _super();

        var SubView = viewRegistry.get('graph');
        var subView = new SubView(this.viewInfo, this.subViewParams);
        var def2 = subView.getController(this).then(function (controller) {
            self.controller = controller;
            return self.controller.appendTo(document.createDocumentFragment());
        });
        return Promise.all([def1, def2]);
    },
    /**
     * @override
     */
    start: function () {
        this.$el.append(this.controller.$el);
        return this._super.apply(this, arguments);
    },
    /**
     * Call `on_attach_callback` for each subview
     *
     * @override
     */
    on_attach_callback: function () {
        this.controller.on_attach_callback();
    },
});

widgetRegistry.add('pie_chart', PieChart);

return PieChart;

});
