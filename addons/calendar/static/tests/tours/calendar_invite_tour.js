import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

/**
 * Add a partner to the partner_ids field by searching for them by name.
 */
function addPartner(partnerName) {
    return [
        {
            content: "Open the dropdown menu of the partner_ids field.",
            trigger: ".o_field_widget[name='partner_ids'] input",
            run: "click",
        },
        {
            content: "Open the search modal to find a partner.",
            trigger: 'div[name="partner_ids"] .o_m2o_dropdown_option_search_more',
            run: "click",
        },
        {
            content: "Search for a partner.",
            trigger: ".o_searchview_input",
            run: `edit ${partnerName}`,
        },
        {
            content: "Validate the name entered in the search bar.",
            trigger: ".o_searchview_autocomplete:contains('Search Name')",
            run: "press Enter",
        },
        {
            content: "Select the returned partner to add it to the partner_ids field.",
            trigger: `.o_dialog:contains("Search: Attendees") td:contains("${partnerName}")`,
            run: "click",
        },
    ];
}

registry.category("web_tour.tours").add("calendar_invite_tour", {
    steps: () => [
        ...addPartner("Past Event Partner"), // Add a partner to a past event.
        ...stepUtils.saveForm(),
        {
            content: "Check that the modal allowing to send invitations is not displayed for past events.",
            trigger: "body:not(.modal-content:contains('Would you like to send invitation emails to attendees?'))",
        },
        stepUtils.goToUrl("/odoo/calendar/"),
        {
            content: "Click on the New button to create a new event",
            trigger: '.o-calendar-button-new',
            run: "click",
        },
        {
            content: "Add a name to the new event.",
            trigger: 'div[name="name"] input',
            run: "edit Upcoming Event",
        },
        ...addPartner("Created Event Partner"),
        ...stepUtils.saveForm(),
        {
            content: "Check that the modal allowing to send invitations is displayed when creating an event with an attendee.",
            trigger: ".modal-content:contains('Would you like to send invitation emails to attendees?') button:contains('send')",
            run: "click",
        },
        ...addPartner("Updated Event Partner"),
        ...stepUtils.saveForm(),
        {
            content: "Check that the modal allowing to send invitations is displayed when updating an event with an new attendee.",
            trigger: ".modal-content:contains('Would you like to send invitation emails to attendees?') button:contains('send')",
            run: "click",
        },
    ],
});
