/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('hr_recruitment_tour',{
    url: "/web",
    rainbowManMessage: () => markup(_t("<div>Great job! You hired a new colleague!</div><div>Try the Website app to publish job offers online.</div>")),
    fadeout: 'very_slow',
    sequence: 230,
    steps: () => [stepUtils.showAppsMenuItem(), {
    isActive: ["community"],
    trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
    content: markup(_t("Let's have a look at how to <b>improve</b> your <b>hiring process</b>.")),
    position: 'right',
    run: "click",
}, {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
    content: markup(_t("Let's have a look at how to <b>improve</b> your <b>hiring process</b>.")),
    position: 'bottom',
    run: "click",
}, {
    trigger: ".o-kanban-button-new",
    content: _t("Create your first Job Position."),
    position: "bottom",
    run: "click",
}, 
{
    isActive: ["auto"],
    trigger: ".o_hr_job_simple_form",
},
{
    trigger: ".o_job_name",
    content: _t("What do you want to recruit today? Choose a job title..."),
    position: "right",
    run: "click",
}, 
{
    isActive: ["auto"],
    trigger: '.o_hr_job_simple_form',
},
{
    trigger: ".o_job_alias",
    content: _t("Choose an application email."),
    position: "right",
    run: "click",
}, {
    trigger: '.o_create_job',
    content: _t('Let\'s create the position. An email will be setup for applications, and a public job description, if you use the Website app.'),
    position: 'bottom',
    run: "click .modal:visible .btn.btn-primary",
}, {
    trigger: ".o_copy_paste_email",
    content: _t("Copy this email address, to paste it in your email composer, to apply."),
    position: "bottom",
    run: "click",
}, 
{
    isActive: ["auto"],
    trigger: ".o_kanban_applicant",
},
{
    trigger: ".breadcrumb-item:not(.active):last",
    content: _t("Let’s go back to the dashboard."),
    position: "bottom",
    run: "click",
}, 
{
    isActive: ["auto"],
    trigger: ".o_hr_recruitment_kanban",
},
{
    trigger: ".oe_kanban_action_button",
    content: markup(_t("<b>Did you apply by sending an email?</b> Check incoming applications.")),
    position: "bottom",
    run: "click",
}, 
{
    isActive: ["auto"],
    trigger: ".o_kanban_applicant",
},
{
    trigger: ".oe_kanban_card",
    content: markup(_t("<b>Drag this card</b>, to qualify him for a first interview.")),
    position: "bottom",
    run: "drag_and_drop(.o_kanban_group:eq(1))",
}, 
{
    isActive: ["auto"],
    trigger: ".o_kanban_applicant",
},
{
    trigger: ".oe_kanban_card",
    content: markup(_t("<b>Click to view</b> the application.")),
    position: "bottom",
    run: "click",
}, 
{
    isActive: ["auto"],
    trigger: ".o_applicant_form",
},
{
    trigger: "button:contains(Send message)",
    content: markup(_t("<div><b>Try to send an email</b> to the applicant.</div><div><i>Tips: All emails sent or received are saved in the history here</i>")),
    position: "bottom",
    run: "click",
}, 
{
    isActive: ["auto"],
    trigger: ".o_applicant_form",
},
{
    trigger: ".o-mail-Chatter .o-mail-Composer button[aria-label='Send']",
    content: _t("Send your email. Followers will get a copy of the communication."),
    position: "bottom",
    run: "click",
}, 
{
    isActive: ["auto"],
    trigger: ".o_applicant_form",
},
{
    trigger: "button:contains(Log note)",
    content: _t("Or talk about this applicant privately with your colleagues."),
    position: "bottom",
    run: "click",
}, 
{
    isActive: ["auto"],
    trigger: ".o_applicant_form",
},
{
    trigger: ".o_create_employee",
    content: _t("Let’s create this new employee now."),
    position: "bottom",
    run: "click",
}, 
{
    isActive: ["auto"],
    trigger: ".o_hr_employee_form_view",
},
{
    trigger: ".o_form_button_save",
    content: _t("Save it!"),
    position: "bottom",
    run: "click",
}]});
