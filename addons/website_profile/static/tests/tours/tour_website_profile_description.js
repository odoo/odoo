/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_profile_description', {
    url: "/profile/users",
    steps: () => [{
        content: "Click on one user profile card",
        trigger: "div[onclick]:contains(\"test_user\")",
        run: "click",
    }, {
        content: "Edit profile",
        trigger: "a:contains('EDIT PROFILE')",
        run: "click",
    }, {
        content: "Add some content",
        trigger: ".odoo-editor-editable p",
        run: "editor content <p>code here</p>",
    }, {
        content: "Save changes",
        trigger: "button:contains('Update')",
        run: "click",
    }, {
        content: "Check the content is saved",
        trigger: "span[data-oe-field='website_description']:contains('content <p>code here</p>')",
    }]
})
