odoo.define('hr.applicant.view.kanban', function (require) {
"use strict";
    var core = require('web.core');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var viewRegistry = require('web.view_registry');

    var QWeb = core.qweb;

    var ApplicantKanbanController = KanbanController.extend({
        /**
         * Extends the renderButtons function of KanbanView by adding a button
         * on the applicant view.
         *
         * @override
         */
        renderButtons: function () {
            this._super.apply(this, arguments);
            this.$buttons.append($(QWeb.render("ApplicantKanbanView.populate_button", this)));
            var self = this;
            this.$buttons.on('click', '.o_button_recruitment_populate', function () {
                self.do_action('hr_recruitment_skills.hr_recruitment_populate_wizard_action', {
                    additional_context: {active_id: self.model.get(self.handle).context.active_id},
                    on_close: function () {
                        self.trigger_up('reload');
                    }
                });
            });
        },

        _onSearch: async function (searchQuery) {
            this._super.apply(this, arguments);
            var activeID = this.model.get(this.handle).context.active_id;
            var jobID = undefined;
            if (searchQuery.domain && !_.isEmpty(searchQuery.domain)) {
                searchQuery.domain.forEach(elem => {
                    if (elem.length === 3 && elem[0] === 'job_id') {
                        jobID = elem[2];
                    }
                })
            }
            if (activeID === jobID) {
                $('button.o_button_recruitment_populate').removeClass('d-none');
            } else {
                $('button.o_button_recruitment_populate').addClass('d-none');
            }
        }
    });

    var PayslipKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: ApplicantKanbanController,
        }),
    });

    viewRegistry.add('hr_applicant_kanban', PayslipKanbanView);

    return ApplicantKanbanController;
});
