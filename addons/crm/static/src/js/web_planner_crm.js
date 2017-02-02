odoo.define('planner_crm.planner', function (require) {
"use strict";

var planner = require('web.planner.common');
var core = require('web.core');
var _t = core._t;

planner.PlannerDialog.include({
    prepare_planner_event: function() {
        var self = this;
        this._super.apply(this, arguments);
        if(self.planner['planner_application'] == 'planner_crm') {
            var stages = {
                'solution_selling': [
                    _t('Territory'), _t('Qualified'), _t('Qualified Sponsor'),
                    _t('Proposal'), _t('Negotiation'), _t('Won'), '',
                    _t('New propspect assigned to the right salesperson'),
                    _t('Set fields: Expected Revenue, Expected Closing Date, Next Action'),
                    _t('You are in discussion with the decision maker and HE agreed on his pain points'),
                    _t('Quotation sent to customer'), _t('The customer came back to you to discuss your quotation'),
                    _t('Quotation signed by the customer'), ''],
                'b2c': [
                    _t('New'), _t('Initial Contact'), _t('Product Demonstration'), _t('Proposal'), _t('Won'), '', '',
                    '', _t('Phone call with following questions: ...'),
                    _t('Meeting with a demo. Set Fields: expected revenue, closing date'),
                    _t('Quotation sent'), '', '', ''],
                'b2b': [
                    _t('New'), _t('Qualified'), _t('Needs assessment'), _t('POC Sold'), _t('Demonstration'), _t('Proposal'), _t('Won'),
                    _t('Set fields: Expected Revenue, Expected Closing Date, Next Action'),
                    _t('Close opportunity if: "pre-sales days * $500" < "expected revenue" * probability'),
                    _t('GAP analysis with customer'), _t('Create a Proof of Concept with consultants'),
                    _t('POC demonstration to the customer'), _t('Final Proposal sent'), ''],
                'odoo_default': [
                    _t('New'), _t('Qualified'), _t('Proposition'), _t('Negotiation'), _t('Won'), _t('Lost'), '',
                    '', '', '', '', '', '', '']
            }
            self.$el.on('change', '#input_element_pipeline', function(ev) {
                var option = $(ev.target).find(":selected").val();
                if (_.has(stages, option)) {
                    var values = stages[option];
                    for(var i=0; i<values.length; i++) {
                        $('#input_element_stage_'+i).val(values[i]);
                    }
                }
            });
        }
    }
});

});
