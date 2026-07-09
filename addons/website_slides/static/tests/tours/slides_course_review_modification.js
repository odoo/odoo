import { registry } from "@web/core/registry";
import slidesTourTools from "@website_slides/../tests/tours/slides_tour_tools";

registry.category("web_tour.tours").add("course_review_modification", {
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
            content: 'Show the review tab to reveal the "Add your review" button',
            trigger: "a[id=review-tab]",
            run: "click",
        },
        {
            content: "Open modal to add the first review",
            trigger: ".o_rating_popup_composer_btn:contains(Add your review)",
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
        ...slidesTourTools.openMessageAction("First review", "edit"),
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
        ...slidesTourTools.openMessageAction("Second review", "delete"),
        {
            content: "Confirm the deletion (in a modal)",
            trigger: "#chatterRoot:shadow .modal button:contains(Delete)",
            run: "click",
        },
        {
            content: "Check the number of review displayed on the tab (no number as no review)",
            trigger: "a[id=review-tab]:contains(Reviews):not(:contains(1))",
            run: "click",
        },
        {
            content: "Check that the message has been deleted",
            trigger: "#chatterRoot:shadow .o-mail-Thread-empty:contains(No messages yet.)",
        },
        {
            content: "Add your review button is re-displayed as the user has no rating anymore",
            trigger: ".o_rating_popup_composer_btn:contains(Add your review)",
        },
    ],
});

registry.category("web_tour.tours").add("course_review_modification_by_admin", {
    steps: () => [
        {
            trigger: "a:text(Basics of Gardening - Test)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: "a[id=review-tab]:text(Reviews (1))",
            run: "click",
        },
        {
            trigger: ".o_rating_popup_composer_btn:contains(Add your review)",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:contains(Non admin user review) .o_website_rating_static[title='3 stars on 5']",
        },
        ...slidesTourTools.openMessageAction("Non admin user review", "edit", false),
        {
            trigger: "#chatterRoot:shadow .o-mail-Message .o-mail-Composer-input",
            run: "edit Admin edited this review.",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message button:text(save)",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-body:contains(Admin edited this review.)",
        },
        // If it fails here, it means that the default values have changed after the admin edited someone else's review.
        {
            trigger: ".o_rating_popup_composer_btn:contains(Add your review)",
            run: "click",
        },
        {
            trigger: "div.o_portal_chatter_composer textarea",
            run: "edit New comment from admin",
        },
        {
            trigger:
                ".modal.modal_shown.show button.o_portal_chatter_composer_btn:text(Post review)",
            run: "click",
        },
        {
            trigger: "a[id=review-tab]:text(Reviews (2))",
            run: "click",
        },
        ...slidesTourTools.openMessageAction("Admin edited this review.", "edit"),
        {
            trigger: "#chatterRoot:shadow .o-dropdown-item:has(:text(Delete))",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .modal button:text(Delete)",
            run: "click",
        },
        {
            trigger: "a[id=review-tab]:text(Reviews (1))",
            run: "click",
        },
        // If it fails here, it means that the default values have changed after the admin deleted someone else's review.
        ...slidesTourTools.openMessageAction("New comment from admin", "edit"),
        {
            trigger:
                ".modal.modal_shown.show button.o_portal_chatter_composer_btn:contains(Update review)",
            run: "click",
        },
        {
            trigger: "a[id=home-tab]",
            run: "click",
        },
        {
            trigger: 'a.o_wslides_js_slides_list_slide_link:contains("Gardening: The Know-How")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: 'a[title="Exit Fullscreen"]',
            run: "click",
            expectUnloadPage: true,
        },
        { trigger: "a[href='#discuss'].active:text(Comments (4))" },
        {
            trigger: "#chatterRoot:shadow .o-mail-Composer-input",
            run: "edit Test comment",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Composer-send:enabled",
            run: "click",
        },
        { trigger: "a[href='#discuss']:text(Comments (5))" },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message",
            run: "hover && click #chatterRoot:shadow .o-mail-Message [title='Expand']",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-moreMenu [name='delete']",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .modal button:contains(Delete)",
            run: "click",
        },
        { trigger: "a[href='#discuss']:text(Comments (4))" },
    ],
});
