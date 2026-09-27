import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('event_portal', {
    steps: () => [
        {
            content: 'Only the accessible registrations should be displayed',
            trigger: '.o_portal_my_doc_table',
            run: () => {
                const registrations = [...document.querySelectorAll('tbody tr')];
                if (registrations.length != 2) {
                    throw new Error(`Incorrect number of event registrations in portal: expected 2, found ${registrations.length}.`);
                }
            }
        },
        {
            content: 'Registration booked by portal user should be visible.',
            trigger: '.o_portal_my_doc_table tr:contains("Booked")',
        },
        {
            content: 'Registration with sale order assigned to portal user should be visible.',
            trigger: '.o_portal_my_doc_table tr:contains("Assigned SO")',
        },
        {
            content: 'Downloading event ticket should work.',
            trigger: '.o_portal_my_doc_table tbody tr a[type="button"]',
            run: async function () {
                const response = await fetch(this.anchor.href);
                if (!response.ok) {
                    throw new Error(`Portal event ticket download failed with status ${response.status}`);
                }
                const contentType = response.headers.get("Content-Type");
                if (contentType !== "application/pdf") {
                    throw new Error(`Unexpected portal event ticket content type: ${contentType}`);
                }
            },
        },
        {
            content: 'Open event link.',
            trigger: '.o_portal_my_doc_table tbody tr a:contains("Test Event")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: 'Check that we are on the event website page.',
            trigger: '.o_wevent_event',
        },
    ]
});
