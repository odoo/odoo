import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("course_review_modification", {
    url: "/slides",
    steps: () => [
        {
            trigger: "a:contains(Basics of Gardening - Test)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: 'a:contains("Join this Course")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
        },
        {
            content: 'Show the review tab to reveal the "Add Review" button',
            trigger: "a[id=review-tab]",
            run: "click",
        },
        {
            content: "Open modal to add the first review",
            trigger: ".o_rating_popup_composer_btn:contains(Add Review)",
            run: "click",
        },
        {
            trigger: ".modal.modal_shown.show div.o_portal_chatter_composer textarea",
            run: "edit First review",
        },
        {
            content: "Post the review (4 stars as it is the default)",
            trigger:
                ".modal.modal_shown.show button.o_portal_chatter_composer_btn:contains(Post review)",
            run: "click",
        },
        {
            content: "Check the average stars",
            trigger: ".o_wslides_course_header .o_website_rating_static[title='4 stars on 5']",
        },
        {
            content: 'Check that the message is not tagged as "edited"',
            trigger:
                "#chatterRoot:shadow .o-mail-Message .o-mail-Message-body:not(:has(Fill the message body)):not(:contains( (edited)))",
        },
        {
            content: "Check the number of review displayed on the tab",
            trigger: "a[id=review-tab]:contains(Reviews (1))",
        },
        {
            content:
                "Check that the review button is not present anymore (edit is done through contextual menu)",
            trigger: ":not(.o_rating_popup_composer_btn)",
        },
        {
            content: 'Click on "edit" action of the contextual menu of the rating message',
            trigger: "#chatterRoot:shadow .o-mail-Message:contains(First review)",
            run: "hover && click #chatterRoot:shadow .o-mail-Message [title='Edit']",
        },
        {
            content: "The modal is opened with the posted message",
            trigger: "div.o_portal_chatter_composer textarea:value(First review)",
            run: "edit Second review",
        },
        {
            content: "Modify the number of stars to 2",
            trigger: ".modal.modal_shown .modal-body i.fa.fa-star:eq(1)",
            run: "click",
        },
        {
            content: "Add an attachment to the post",
            trigger:
                ".modal.modal_shown.show div.o_portal_chatter_composer button.o_portal_chatter_attachment_btn",
            async run({ inputFiles }) {
                const text = new File(["test"], "test.txt", { type: "text/plain" });
                await inputFiles(".o_portal_chatter_composer .o_portal_chatter_file_input", [text]);
            },
        },
        {
            content: "Check that the attachment is displayed in the modal",
            trigger:
                ".o_portal_chatter_composer .o_portal_chatter_attachment_name:contains('test.txt')",
        },
        {
            trigger:
                ".modal.modal_shown.show button.o_portal_chatter_composer_btn:contains(Update review)",
            run: "click",
        },
        {
            content: 'Check that the message is tagged as "edited"',
            trigger:
                "#chatterRoot:shadow .o-mail-Message .o-mail-Message-body:not(:has(Fill the message body)):contains( (edited))",
        },
        {
            content: "Check the average stars",
            trigger: ".o_wslides_course_header .o_website_rating_static[title='2 stars on 5']",
        },
        {
            content: "Check the number of review displayed on the tab",
            trigger: "a[id=review-tab]:contains(Reviews (1))",
            run: "click",
        },
        {
            content: "Check that the attachment is displayed on the posted review",
            trigger: "#chatterRoot:shadow .o-mail-AttachmentCard-info:contains('test.txt')",
        },
        {
            content: "Open the contextual menu on the posted message",
            trigger: '#chatterRoot:shadow .o-mail-Message:contains("Second review")',
            run: "hover && click #chatterRoot:shadow .o-mail-Message [title='Expand']",
        },
        {
            content: 'Click on the "Delete" button of the contextual menu of the message',
            trigger: "#chatterRoot:shadow .o-mail-Message-moreMenu",
            run: "click #chatterRoot:shadow button[name='delete']",
        },
        {
            content: "Confirm the deletion (in a modal)",
            trigger: "#chatterRoot:shadow button:contains(Delete)",
            run: "click",
        },
        {
            content: "Check the number of review displayed on the tab (no number as no review)",
            trigger: "a[id=review-tab]:contains(Reviews):not(:contains(1))",
            run: "click",
        },
        {
            content: "Check that the message has been deleted",
            trigger:
                "#chatterRoot:shadow .o-mail-Thread-empty:contains(The conversation is empty.)",
        },
        {
            content: "Add review button is re-displayed as the user has no rating anymore",
            trigger: ".o_rating_popup_composer_btn:contains(Add Review)",
        },
    ],
});
