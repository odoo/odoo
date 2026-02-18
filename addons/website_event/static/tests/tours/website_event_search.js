import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_website_event_search", {
    steps: () => [
        {
            trigger: '.btn[title="Filter by category"]:contains(Test Category)',
            run: 'click'
        },
        {
            trigger: '.post_link:contains(tag 1)',
            expectUnloadPage: true,
            run: 'click'
        },
        {
            trigger: '.badge.bg-primary:contains(1)',
        },
        {
            trigger: '.page-link:contains(2)',
            expectUnloadPage: true,
            run: 'click'
        },
        {
            content: 'Click on search input',
            trigger: '.o_searchbar_form input',
            run: 'click',
        },
        {
            trigger: '#o_search_modal_events_list .input-group .search-query.form-control',
            run: 'edit Event 0',
        },
        {
            content: 'Wait for the search results to be updated & close the search modal',
            trigger: '.o_searchbar_form .o_dropdown_menu:not(:has(.o_search_result_item_placeholder))',
            run: 'press Escape',
        },
        {
            trigger: '.badge.bg-primary:contains(1)',
            run: () => {}
        },
    ],
});
