import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_hr_recruitment_skills_tour', {
    url: '/jobs',
    steps: () => [{
        content: "Select Job",
        trigger: `.oe_website_jobs h3:contains(Guru)`,
        run: "click",
        expectUnloadPage: true,
    }, {
        content: "Apply",
        trigger: ".js_hr_recruitment a:contains(Apply)",
        run: "click",
        expectUnloadPage: true,
    }, {
        content: "Complete name",
        trigger: "input[name=partner_name]",
        run: `edit John Smith`,
    }, {
        content: "Complete Email",
        trigger: "input[name=email_from]",
        run: `edit john@smith.com`,
    }, {
        content: "Complete phone number",
        trigger: "input[name=partner_phone]",
        run: `edit 118.218`,
    }, {
        content: "Complete LinkedIn profile",
        trigger: "input[name=linkedin_profile]",
        run: `edit linkedin.com/in/john-smith}`,
    }, {
        content: "Complete Skills",
        trigger: "input[name=skill_ids]",
        run: "click"
    }, {
        content: "Complete Subject",
        trigger: "textarea[name=short_introduction]",
        run: `edit ### [GURU] HR RECRUITMENT TEST DATA ###`,
    }, {
        content: "Send the form",
        trigger: ".s_website_form_send",
        run: "click",
        expectUnloadPage: true,
    }, {
        content: "Check the form is submitted without errors",
        trigger: "#jobs_thankyou h1:contains('Congratulations')",
    }],
});
