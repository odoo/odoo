import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Recruitment (Website) Tour
 *
 * Walks the user through the careers pages published from the Website app:
 *  1. Open the Website application and the Recruitment section
 *  2. Browse the job openings
 *  3. Publish a new job opening
 *  4. Review the received applications
 */
registry.category("web_tour.tours").add("od19_recruitment_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "website.menu_website_configuration",
            markup(_t("Let's publish a <b>job opening</b> on the website."))
        ),

        {
            trigger: navSection("Recruitment"),
            content: markup(_t("Open the <b>Recruitment</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Job Openings"),
            content: markup(_t("Open <b>Job Openings</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Job Openings"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each row is a position. <b>Published</b> positions are visible on the " +
                "public <b>/jobs</b> page of the website."
            )),
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to create a job opening.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t("Enter the <b>job title</b>, e.g. Senior Automation Engineer.")),
            run: "edit Senior Automation Engineer",
        },
        {
            trigger: ".o_field_widget[name='department']",
            content: markup(_t("Pick the <b>department</b> the position belongs to.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='job_type']",
            content: markup(_t("Set the <b>contract type</b> (full time, part time, contract…).")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='work_location']",
            content: markup(_t("State the <b>work location</b> shown on the website.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='vacancies']",
            content: markup(_t("Indicate how many <b>vacancies</b> are open.")),
            tooltipPosition: "bottom",
        },
        ...stepUtils.saveForm(),
        {
            trigger: ".o_form_view, .o_form_readonly, .o_form_saved",
            content: markup(_t(
                "The opening is published automatically. Use the " +
                "<b>Overview / Job Description / Qualifications</b> tabs to write the " +
                "content candidates will read on the careers page."
            )),
        },
        ...stepUtils.discardForm(),

        // --- Applications ---
        {
            trigger: navSection("Recruitment"),
            content: markup(_t("Reopen the <b>Recruitment</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Applications"),
            content: markup(_t("Open <b>Applications</b> to read the CVs received.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Applications"),

        {
            trigger: ".o_list_renderer, .o_kanban_view",
            content: markup(_t(
                "Recruitment complete! Publish a job opening → it appears on <b>/jobs</b> → " +
                "candidates apply from the website and land in <b>Applications</b>."
            )),
            run: "click",
        },
    ],
});
