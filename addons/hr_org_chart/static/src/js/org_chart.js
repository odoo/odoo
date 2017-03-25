odoo.define('web.OrgChart', function (require) {
"use strict";

var core = require('web.core');
var common = require('web.form_common');

var QWeb = core.qweb;
var _t = core._t;


var FieldOrgChart = common.AbstractField.extend({
    template: "OrgChart",
    render_value: function() {
        var self = this;
        this.view.dataset.call('get_org_chart', [[this.view.datarecord.id], this.view.datarecord.parent_id[0] || false, this.view.dataset.get_context()]).then(
           function (data) {
              self.data = data
              self.$el.html(QWeb.render("OrgChartDetail", {widget: self, data: data}));
              return data
           }
        );
        this._super();
    },

});

core.form_widget_registry.add('orgchart', FieldOrgChart)

return OrgChart;

});
