/** @odoo-module **/

import { registry } from "@web/core/registry";

const messageOfOtherUserSelector =
    "#chatterRoot:shadow .o-mail-Message:has(.o-mail-Message-textContent:contains('Other user review'))";

/**
 * This tour tests that editing the comment of another user (as admin)
 * doesn't alter the behavior of the "Edit review" button:
 * admins will edit their own review and not another one's they've just edited.
 */
registry.category("web_tour.tours").add("course_reviews_admin", {
    url: "/slides",
    steps: () => [
        {
            trigger: "a:contains(Basics of Gardening - Test)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: "a[id=review-tab]",
            run: "click",
        },
        {
            content: 'Click on "edit" of the rating message of another user',
            trigger: messageOfOtherUserSelector,
            run: `hover && click ${messageOfOtherUserSelector} [title='Edit']`,
        },
        {
            content: "Update the content of the message",
            trigger: "#chatterRoot:shadow .o-mail-Message .o-mail-Composer textarea",
            run: "edit Other user review edited",
        },
        {
            content:
                "Update the Review tab name to detect later when the review is saved (see below)",
            trigger: "body",
            async run() {
                document.getElementById("review-tab").textContent = "Review";
            },
        },
        {
            content: "Click on save",
            trigger: "#chatterRoot:shadow button[data-type=save]",
            run: "click",
        },
        {
            content:
                "Wait the review to be completely saved by checking that the review tab name has been updated",
            trigger: "#review-tab:contains('Reviews (2)')",
        },
        {
            content: 'Click on the "edit review" button to edit the logged user review',
            trigger: ".o_rating_popup_composer_text:contains(Edit Review)",
            run: "click",
        },
        {
            content:
                "Check that the modal displays the message of the logged user and not the one we've just modified",
            trigger: "div.o_portal_chatter_composer_body textarea:value(Admin review)",
        },
        {
            content: "Select 5 stars for the admin review",
            trigger: ".modal.modal_shown .modal-body i.fa.fa-star-o:eq(3)",
            run: "click",
        },
        {
            content: "Update admin review",
            trigger: "div.o_portal_chatter_composer textarea:value(Admin review)",
            run: "edit Admin review2",
        },
        {
            content: "Post admin review",
            trigger:
                ".modal.modal_shown.show button.o_portal_chatter_composer_btn:contains(Update review)",
            run: "click",
        },
        {
            content: "Check that the admin message and review have been updated",
            trigger:
                "#chatterRoot:shadow .o-mail-Message:contains(Admin review2) .o_website_rating_static[title='5 stars on 5']",
        },
    ],
});
