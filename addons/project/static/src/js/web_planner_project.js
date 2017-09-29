odoo.define('planner_project.planner', function (require) {
"use strict";

var planner = require('web.planner.common');
var core = require('web.core');
var _t = core._t;

planner.PlannerDialog.include({
    prepare_planner_event: function() {
        this._super.apply(this, arguments);
        if (this.planner["planner_application"] === "planner_project") {
            var self = this;

            var stages = {
                'development_process': {
                    'input_element_stage_0' : _t('Specification'),
                    'input_element_stage_1' : _t('Validation'),
                    'input_element_stage_2' : _t('Development'),
                    'input_element_stage_3' : _t('Testing'),
                    'input_element_stage_4' : _t('Deployment'),
                    'input_element_stage_5' : '',
                    'input_element_stage_6' : '',
                    'input_element_stage_7' : _t('Specification of task is written'),
                    'input_element_stage_8' : _t('Specification is validated'),
                    'input_element_stage_9' : _t('Task is Developed'),
                    'input_element_stage_10' : _t('Task is tested'),
                    'input_element_stage_11' : _t('Finally task is deployed'),
                    'input_element_stage_12' : '',
                    'input_element_stage_13' : '',
                },
                'marketing_department': {
                    'input_element_stage_0' : _t('Backlog'),
                    'input_element_stage_1' : _t('In progress'),
                    'input_element_stage_2' : _t('Copywriting / Design'),
                    'input_element_stage_3' : _t('Distribute'),
                    'input_element_stage_4' : _t('Done'),
                    'input_element_stage_5' : '',
                    'input_element_stage_6' : '',
                    'input_element_stage_7' : _t('Action has a clear description'),
                    'input_element_stage_8' : _t('Work has started'),
                    'input_element_stage_9' : _t('Ready for layout / copywriting'),
                    'input_element_stage_10' : _t('Ready to be displayed, published or sent'),
                    'input_element_stage_11' : _t('Distribution is completed'),
                    'input_element_stage_12' : '',
                    'input_element_stage_13' : '',
                },
                'scrum_methodology': {
                    'input_element_stage_0' : _t('Backlog'),
                    'input_element_stage_1' : _t('Sprint'),
                    'input_element_stage_2' : _t('Test'),
                    'input_element_stage_3' : _t('Documentation'),
                    'input_element_stage_4' : _t('Release'),
                    'input_element_stage_5' : '',
                    'input_element_stage_6' : '',
                    'input_element_stage_7' : _t('Clear description and purpose'),
                    'input_element_stage_8' : _t('Added in current sprint'),
                    'input_element_stage_9' : _t('Ready for testing'),
                    'input_element_stage_10' : _t('Test is OK, need to document'),
                    'input_element_stage_11' : _t('Ready for release'),
                    'input_element_stage_12' : '',
                    'input_element_stage_13' : '',
                },
                'customer_service': {
                    'input_element_stage_0' : _t('Backlog'),
                    'input_element_stage_1' : _t('New'),
                    'input_element_stage_2' : _t('In progress'),
                    'input_element_stage_3' : _t('Wait. Customer'),
                    'input_element_stage_4' : _t('Wait. Expert'),
                    'input_element_stage_5' : _t('Done'),
                    'input_element_stage_6' : _t('Cancelled'),
                    'input_element_stage_7' : _t('Customer service has found new issue'),
                    'input_element_stage_8' : _t('Customer has reported new issue'),
                    'input_element_stage_9' : _t('Issue is being worked on'),
                    'input_element_stage_10' : _t('Customer feedback has been requested'),
                    'input_element_stage_11' : _t('Expert advice has been requested'),
                    'input_element_stage_12' : _t('Issue is resolved'),
                    'input_element_stage_13' : _t('Reason for cancellation has been documented'),
                },
                'repair_workshop': {
                    'input_element_stage_0' : _t('Incoming'),
                    'input_element_stage_1' : _t('In progress'),
                    'input_element_stage_2' : _t('Wait. Customer'),
                    'input_element_stage_3' : _t('Wait. Expert'),
                    'input_element_stage_4' : _t('Done'),
                    'input_element_stage_5' : _t('Cancelled'),
                    'input_element_stage_6' : '',
                    'input_element_stage_7' : _t('New repair added'),
                    'input_element_stage_8' : _t('Repair has started'),
                    'input_element_stage_9' : _t('Feedback from customer requested'),
                    'input_element_stage_10' : _t('Request for parts has been sent'),
                    'input_element_stage_11' : _t('Repair is completed'),
                    'input_element_stage_12' : _t('Customer has cancelled repair'),
                    'input_element_stage_13' : '',
                },
                'basic_management': {
                    'input_element_stage_0' : _t('Ideas'),
                    'input_element_stage_1' : _t('To Do'),
                    'input_element_stage_2' : _t('Done'),
                    'input_element_stage_3' : _t('Cancelled'),
                    'input_element_stage_4' : '',
                    'input_element_stage_5' : '',
                    'input_element_stage_6' : '',
                    'input_element_stage_7' : _t('Idea is fully explained'),
                    'input_element_stage_8' : _t('Idea has been transformed into concrete actions'),
                    'input_element_stage_9' : _t('Task is completed'),
                    'input_element_stage_10' : _t('Reason for cancellation has been documented'),
                    'input_element_stage_11' : '',
                    'input_element_stage_12' : '',
                    'input_element_stage_13' : '',
                }
            };

            var stage_handler = function (option) {
                if (_.has(stages, option)) {
                    var values = stages[option];
                    var keys = _.keys(values);
                    for(var i=0; i<keys.length; i++) {
                        self.$('#' + keys[i]).val(values[keys[i]]);
                        self.$('#' + keys[i] + '_user').val(values[keys[i]]);
                    }
                }
            };

            self.$('#input_element_kanban_stage_pipeline').on('change', function(ev) {
                var option = self.$(ev.target).find(":selected").val();
                stage_handler(option);
            });
            self.$( ".user_project" ).on('change', function() {
                self.$("#" + self.$(this).attr("id") + "_user").val(self.$(this).val());
            });

            // Load first option by default
            var first_option = self.$('#input_element_kanban_stage_pipeline').find('option').first().val();
            stage_handler(first_option);
        }
    }
});

});
