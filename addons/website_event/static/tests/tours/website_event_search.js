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
            trigger: '.input-group .search-query.form-control',
            run: 'edit Event 0 && click body',
        },
        {
            trigger: '.badge.bg-primary:contains(1)',
            run: () => {}
        },
    ],
});
