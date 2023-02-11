odoo.define('website_hr_recruitment.tour', function(require) {
    'use strict';

    var tour = require("web_tour.tour");
    function applyForAJob(jobName, application) {
        return [{
            content: "Select Job",
            trigger: `.oe_website_jobs h3 span:contains(${jobName})`,
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
            content: "Complete Subject",
            trigger: "textarea[name=description]",
            run: `text ${application.subject}`,
        }, { // TODO: Upload a file ?
            content: "Send the form",
            trigger: ".s_website_form_send",
        }, {
            content: "Check the form is submitted without errors",
            trigger: ".oe_structure:has(h1:contains('Congratulations'))",
        }];
    }

    tour.register('website_hr_recruitment_tour', {
        test: true,
        url: '/jobs',
    }, [
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
    ]);

    tour.register('website_hr_recruitment_tour_edit_form', {
        test: true,
        url: '/jobs',
    }, [{
        content: 'Go to the Guru job page',
        trigger: 'a[href*="guru"]',
    }, {
        content: 'Go to the Guru job form',
        trigger: 'a[href*="apply"]',
    }, {
        content: 'Check if the Guru form is present',
        trigger: 'form'
    }, {
        content: 'Enter in edit mode',
        trigger: 'a[data-action="edit"]',
    }, {
        content: 'Add a fake default value for the job_id field',
        trigger: 'button[data-action="save"]',
        run: () => {
            // It must be done in this way because the editor does not allow to
            // put a default value on a field with type="hidden".
            document.querySelector('input[name="job_id"]').value = 'FAKE_JOB_ID_DEFAULT_VAL';
        },
    }, {
        content: 'Edit the form',
        trigger: 'input[type="file"]',
        extra_trigger: '#oe_snippets.o_loaded',
    }, {
        content: 'Add a new field',
        trigger: 'we-button[data-add-field]',
    }, {
        content: 'Save',
        trigger: 'button[data-action="save"]',
    }, {
        content: 'Go back to /jobs page after save',
        trigger: 'a[data-action="edit"]',
        run: () => {
            window.location.href = '/jobs';
        }
    }, {
        content: 'Go to the Internship job page',
        trigger: 'a[href*="internship"]',
    }, {
        content: 'Go to the Internship job form',
        trigger: 'a[href*="apply"]',
    }, {
        content: 'Check that a job_id has been loaded',
        trigger: 'form',
        run: () => {
            const selector =
                'input[name="job_id"]:not([value=""]):not([value = "FAKE_JOB_ID_DEFAULT_VAL"])';
            if (!document.querySelector(selector)) {
                console.error('The job_id field has a wrong value');
            }
        }
    }, {
        content: 'Enter in edit mode',
        trigger: 'a[data-action="edit"]',
    }, {
        content: 'Verify that the job_id field has kept its default value',
        trigger: 'button[data-action="save"]',
        run: () => {
            if (!document.querySelector('input[name="job_id"][value="FAKE_JOB_ID_DEFAULT_VAL"]')) {
                console.error('The job_id field has lost its default value');
            }
        }
    },
]);

    return {};
});
