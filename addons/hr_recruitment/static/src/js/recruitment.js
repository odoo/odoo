/** @odoo-module **/
import KanbanRecord from 'web.KanbanRecord';

import fieldRegistry from 'web.field_registry';
import { FieldChar, StateSelectionWidget } from 'web.basic_fields';

const RecruitmentStateSelectionWidget = StateSelectionWidget.extend({
    init() {
        this._super(...arguments);
        this.mode = 'edit';
    },
});

const ApplicantChar = FieldChar.extend({
    events: _.extend({}, FieldChar.prototype.events, {
        'click': '_onClick',
    }),

    _onClick(ev) {
        if (this.recordData['res_id'] !== undefined && this.recordData['res_model'] === 'hr.applicant') {
            ev.stopPropagation();

            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'hr.applicant',
                res_id: this.recordData['res_id'],
                views: [[false, "form"]],
                view_mode: "form",
                target: "current",
            });
        }
    },

    _renderReadonly() {
        this._super(...arguments);
        this.$el.addClass('o_hr_applicant_widget');
    }
});

fieldRegistry
    .add('recruitment_state_selection', RecruitmentStateSelectionWidget)
    .add('applicant_char', ApplicantChar);

KanbanRecord.include({
    /**
     * @override
     * @private
     */
    _openRecord: function () {
        if (this.modelName === 'hr.job' && this.$(".o_hr_job_boxes a").length) {
            this.$(".o_hr_job_boxes a").first().click();
        } else {
            this._super.apply(this, arguments);
        }
    }
});
