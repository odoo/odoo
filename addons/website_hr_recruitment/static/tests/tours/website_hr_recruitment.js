/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import wTourUtils from "@website/js/tours/tour_utils";

    function applyForAJob(jobName, application) {
        return [{
            content: "Select Job",
            trigger: `.oe_website_jobs h3:contains(${jobName})`,
        }, {
            content: "Apply",
            trigger: ".js_hr_recruitment a:contains('Apply')",
        }, {
            content: "Complete name",
            trigger: "input[name=partner_name]",
            run: `text ${application.name}`,
        }, {
            content: "Complete Email",
            trigger: "input[name=email_from]",
            run: `text ${application.email}`,
        }, {
            content: "Complete phone number",
            trigger: "input[name=partner_phone]",
            run: `text ${application.phone}`,
        }, {
            content: "Complete LinkedIn profile",
            trigger: "input[name=linkedin_profile]",
            run: `text linkedin.com/in/${application.name.toLowerCase().replace(' ', '-')}`,
        }, {
            content: "Complete Subject",
            trigger: "textarea[name=description]",
            run: `text ${application.subject}`,
        }, { // TODO: Upload a file ?
            content: "Send the form",
            trigger: ".s_website_form_send",
        }, {
            content: "Check the form is submitted without errors",
            trigger: "#jobs_thankyou h1:contains('Congratulations')",
            isCheck: true,
        }];
    }

    registry.category("web_tour.tours").add('website_hr_recruitment_tour', {
        test: true,
        url: '/jobs',
        steps: () => [
        ...applyForAJob('Guru', {
            name: 'John Smith',
            email: 'john@smith.com',
            phone: '118.218',
            subject: '### [GURU] HR RECRUITMENT TEST DATA ###',
        }),
        {
            content: "Go back to the jobs page",
            trigger: "body",
            run: () => {
                window.location.href = '/jobs';
            },
        },
        ...applyForAJob('Internship', {
            name: 'Jack Doe',
            email: 'jack@doe.com',
            phone: '118.712',
            subject: '### HR [INTERN] RECRUITMENT TEST DATA ###',
        }),
    ]});

    wTourUtils.registerWebsitePreviewTour('website_hr_recruitment_tour_edit_form', {
        test: true,
        url: '/jobs',
    }, () => [{
        content: 'Go to the Guru job page',
        trigger: 'iframe a[href*="guru"]',
    }, {
        content: 'Go to the Guru job form',
        trigger: 'iframe a[href*="apply"]',
    }, {
        content: 'Check if the Guru form is present',
        trigger: 'iframe form'
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: 'Add a fake default value for the job_id field',
        trigger: "body",
        run: () => {
            // It must be done in this way because the editor does not allow to
            // put a default value on a field with type="hidden".
            document.querySelector('.o_iframe:not(.o_ignore_in_tour)').contentDocument.querySelector('input[name="job_id"]').value = 'FAKE_JOB_ID_DEFAULT_VAL';
        },
    }, {
        content: 'Edit the form',
        trigger: 'iframe input[type="file"]',
    }, {
        content: 'Add a new field',
        trigger: 'we-button[data-add-field]',
    },
    ...wTourUtils.clickOnSave(),
    {
        content: 'Go back to /jobs page after save',
        trigger: 'iframe body',
        run: () => {
            window.location.href = wTourUtils.getClientActionUrl('/jobs');
        }
    }, {
        content: 'Go to the Internship job page',
        trigger: 'iframe a[href*="internship"]',
    }, {
        content: 'Go to the Internship job form',
        trigger: 'iframe a[href*="apply"]',
    }, {
        content: 'Check that a job_id has been loaded',
        trigger: 'iframe form',
        run: () => {
            const selector =
                'input[name="job_id"]:not([value=""]):not([value = "FAKE_JOB_ID_DEFAULT_VAL"])';
            if (!document.querySelector('.o_iframe:not(.o_ignore_in_tour)').contentDocument.querySelector(selector)) {
                console.error('The job_id field has a wrong value');
            }
        }
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: 'Verify that the job_id field has kept its default value',
        trigger: "body",
        run: () => {
            const doc = document.querySelector(".o_iframe:not(.o_ignore_in_tour)").contentDocument;
            const id = doc.querySelector('[data-oe-model="hr.job"]').dataset.oeId;
            if (!doc.querySelector(`input[name="job_id"][value="${id}"]`)) {
                console.error('The job_id field has lost its default value');
            }
        }
    },
]);

    // This tour addresses an issue that occurred in a website form containing
    // the 'hide-change-model' attribute. Specifically, when a model-required
    // field is selected, the alert message should not display an undefined
    // action name.
    wTourUtils.registerWebsitePreviewTour('model_required_field_should_have_action_name', {
        test: true,
        url: '/jobs',
    }, () => [{
        content: "Select Job",
        trigger: "iframe h3:contains('Guru')",
    }, {
        content: "Apply",
        trigger: "iframe a:contains('Apply')",
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "click on the your name field",
        trigger: "iframe #hr_recruitment_form div.s_website_form_model_required",
    }, {
        content: "Select model-required field",
        trigger: "we-customizeblock-options we-alert > span:not(:contains(undefined))",
        isCheck: true,
    }
]);

export default {};
