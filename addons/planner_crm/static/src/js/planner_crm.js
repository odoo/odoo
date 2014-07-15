(function(){
    "use strict";

    openerp.qweb.add_template('/planner_crm/static/src/xml/planner_crm.xml');

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

    openerp.web.planner_crm = function() {
        $('#input_element_pipeline').change(function(ev) {
            var option = $(ev.target).find(":selected").val();
            if (_.has(stages, option)) {
                var values = stages[option];
                for(var i=0; i<14; i++) {
                    $('#input_element_stage_'+i+'').val(values[i]);
                }
            }
        });
    }

})();
