import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_website_event_mobile_filter_offcanvas", {
    steps: () => [
        {
            content: "Switch to mobile view",
            trigger: ".o_mobile_preview .fa-mobile",
            run: "click",
        },
        // Verify no filters active initially: no o_filter_tag, no red dot.
        {
            content: "Verify no active filter tags are shown initially",
            trigger: ":iframe .o_wevent_index:not(:has(.o_filter_tag))",
        },
        {
            content: "Verify red dot is NOT shown on filter button initially",
            trigger:
                ":iframe .o_wevent_search button[data-bs-target='#o_wevent_index_offcanvas']:not(:has(.bg-danger))",
        },
        // Open mobile filter offcanvas and wait for it to be visible.
        {
            content: "Open mobile filter offcanvas",
            trigger: ":iframe .o_wevent_search button[data-bs-target='#o_wevent_index_offcanvas']",
            run: "click",
        },
        {
            content: "Wait for offcanvas to be fully visible",
            trigger: ":iframe #o_wevent_index_offcanvas.show",
        },
        {
            content: "Expand the tag filter accordion",
            trigger: ":iframe #o_wevent_index_offcanvas .accordion-button.collapsed",
            run: "click",
        },
        {
            content: "Wait for accordion to be expanded",
            trigger: ":iframe #o_wevent_index_offcanvas .accordion-collapse.show",
        },
        // Select 3 tag checkboxes and apply filters.
        {
            content: "Select first tag checkbox",
            trigger:
                ":iframe #o_wevent_index_offcanvas input.form-check-input[name='tags']:not(:checked)",
            run: "click",
        },
        {
            content: "Select second tag checkbox",
            trigger:
                ":iframe #o_wevent_index_offcanvas input.form-check-input[name='tags']:not(:checked)",
            run: "click",
        },
        {
            content: "Select third tag checkbox",
            trigger:
                ":iframe #o_wevent_index_offcanvas input.form-check-input[name='tags']:not(:checked)",
            run: "click",
        },
        {
            content: "Click Apply Filters",
            trigger: ":iframe #o_wevent_index_offcanvas .o_mobile_filter_apply",
            run: "click",
        },
        // Verify filters are applied: 3 filter tags shown, red dot on filter
        // button.
        {
            content: "Verify Culture filter tag is shown after apply",
            trigger: ":iframe .o_filter_tag:contains('Culture')",
        },
        {
            content: "Verify Tech filter tag is shown after apply",
            trigger: ":iframe .o_filter_tag:contains('Tech')",
        },
        {
            content: "Verify Business filter tag is shown after apply",
            trigger: ":iframe .o_filter_tag:contains('Business')",
        },
        {
            content: "Verify red dot appears on filter button when filters are active",
            trigger:
                ":iframe .o_wevent_search button[data-bs-target='#o_wevent_index_offcanvas'] .bg-danger",
        },
        // Re-open offcanvas to clear all filters.
        {
            content: "Re-open mobile filter offcanvas",
            trigger: ":iframe .o_wevent_search button[data-bs-target='#o_wevent_index_offcanvas']",
            run: "click",
        },
        {
            content: "Wait for offcanvas to be fully visible again",
            trigger: ":iframe #o_wevent_index_offcanvas.show",
        },
        {
            content: "Click Clear Filters",
            trigger: ":iframe #o_wevent_index_offcanvas .o_mobile_filter_clear",
            run: "click",
        },
        // Verify filters are cleared: no filter tags, no red dot.
        {
            content: "Verify no active filter tags remain after clear",
            trigger: ":iframe .o_wevent_index:not(:has(.o_filter_tag))",
        },
        {
            content: "Verify red dot is gone after clear",
            trigger:
                ":iframe .o_wevent_search button[data-bs-target='#o_wevent_index_offcanvas']:not(:has(.bg-danger))",
        },
    ],
});
