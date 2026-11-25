import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('survey_tour', {
    steps: () => [
    ...stepUtils.goToAppSteps('survey.menu_surveys', markup(_t("Ready to change the way you <b>gather data</b>?"))),
{
    trigger: 'article .o_survey_kanban_card div:contains("Feedback Form")',
    content: _t('Open the "Feedback Form" survey'),
    run: "click",
}, {
    trigger: 'button[name=action_test_survey]',
    content: _t("Let's give it a spin!"),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: 'button[type=submit]',
    content: _t("Let's get started!"),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: '.o_survey_question:contains("How frequently") input',
    content: _t("Pick an answer!"),
    tooltipPosition: 'left',
    run: 'click'
},
{
    trigger: '.o_survey_question:contains("How many") input',
    content: _t("Enter a number!"),
    tooltipPosition: 'left',
    run: 'edit 5'
},
{
    trigger: 'button[type=submit]',
    content: _t("Let's continue to the next page!"),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: '.o_survey_question:contains("Which of") input',
    content: _t("Let's pick an answer again!"),
    tooltipPosition: 'left',
    run: 'click'
},
{
    trigger: '.o_survey_question:contains("What do") tbody tr:eq(0) input',
    content: _t("Just one question left!"),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: '.o_survey_question:contains("What do") tbody tr:eq(1) input',
    content: _t("Matrix questions have multiple lines!"),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: '.o_survey_question:contains("What do") tbody tr:eq(2) input',
    content: _t("Answer every one of them!"),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: '.o_survey_question:contains("What do") tbody tr:eq(3) input',
    content: _t("Here you go!"),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: '.o_survey_question:contains("What do") tbody tr:eq(4) input',
    content: _t("Finally!"),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    trigger: 'button[value=finish]',
    content: _t("Now that you are done, submit your form."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.o_survey_review',
    content: _t("Let's have a look at your answers!"),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.survey_button_form_view_hook',
    content: _t("Now, use this shortcut to go back to the survey."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: 'button[name=action_survey_user_input_completed]',
    content: _t("Here, you can view the participants."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: 'td[name=survey_id]',
    content: _t("Let's open the survey you just submitted."),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: '.breadcrumb-item',
    content: _t("Use the breadcrumbs to quickly go back to the survey."),
    tooltipPosition: 'top',
    run: "click",
}, {
    trigger: '.o_popover .o-dropdown-item',
    content: _t("Use the breadcrumbs to quickly go back to the survey."),
    tooltipPosition: 'right',
    run: "click",
}
]});
