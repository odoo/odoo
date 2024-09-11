odoo.define('website_profile.tour_website_profile_description', function (require) {
    'use strict';

    var tour = require("web_tour.tour");

    tour.register("website_profile_description", {
            test: true,
            url: "/profile/users",
        }, [{
            content: "Click on one user profile card",
            trigger: "div[onclick]",
        },{
            content: "Edit profile",
            trigger: "a:contains('EDIT PROFILE')",
        }, {
            content: "Add some content",
            trigger: ".odoo-editor-editable p",
            run: "text content <p>code here</p>",
        }, {
            content: "Save changes",
            trigger: "button:contains('Update')",
        }, {
            content: "Check the content is saved",
            trigger:
                "span[data-oe-field='website_description']:contains('content <p>code here</p>')",
        }]
    );
});
