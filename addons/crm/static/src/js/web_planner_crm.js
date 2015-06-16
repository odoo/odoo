odoo.define('planner_crm.planner', function (require) {
"use strict";

var planner = require('web.planner.common');

planner.PlannerDialog.include({
    prepare_planner_event: function() {
        var self = this;
        this._super.apply(this, arguments);
        if(self.planner['planner_application'] == 'planner_crm') {
            var stages = {
                'solution_selling': [
                    'Territory', 'Qualified', 'Qualified Sponsor',
                    'Proposal', 'Negotiation', 'Won', '',
                    'New propspect assigned to the right salesperson',
                    'Set fields: Expected Revenue, Expected Closing Date, Next Action',
                    'You are in discussion with the decision maker and HE agreed on his pain points',
                    'Quotation sent to customer', 'The customer came back to you to discuss your quotation',
                    'Quotation signed by the customer', ''],
                'b2c': [
                    'New', 'Initial Contact', 'Product Demonstration', 'Proposal', 'Won', '', '',
                    '', 'Phone call with following questions: ...',
                    'Meeting with a demo. Set Fields: expected revenue, closing date',
                    'Quotation sent', '', '', ''],
                'b2b': [
                    'New', 'Qualified', 'Needs assessment', 'POC Sold', 'Demonstration', 'Proposal', 'Won',
                    'Set fields: Expected Revenue, Expected Closing Date, Next Action',
                    'Close opportunity if: "pre-sales days * $500" < "expected revenue" * probability',
                    'GAP analysis with customer', 'Create a Proof of Concept with consultants',
                    'POC demonstration to the customer', 'Final Proposal sent', ''],
                'odoo_default': [
                    'New', 'Qualified', 'Proposition', 'Negotiation', 'Won', 'Lost', '',
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
