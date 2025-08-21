import { registry } from "@web/core/registry";
import { inputFiles } from "@web/../tests/utils";

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
            trigger: "span:contains(Add Review)",
            run: "click",
        },
        {
            trigger: ".modal.modal_shown.show div.o_portal_chatter_composer textarea",
            run: "edit First review",
        },
        {
            trigger:
                ".modal.modal_shown.show button.o_portal_chatter_composer_btn:contains(Post review)",
            run: "click",
        },
        {
            trigger: ".o_wslides_course_header .o_website_rating_static[title='4 stars on 5']",
        },
        {
            trigger: "a[id=review-tab]:contains(Reviews (1))",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:contains(First review)",
            run: "hover && click #chatterRoot:shadow .o-mail-Message [title='Delete']",
        },
        {
            trigger: "#chatterRoot:shadow button:contains(Delete)",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread:contains(The conversation is empty.)",
        },
        {
            trigger: ".o_wslides_course_header .o_website_rating_static[title='0 stars on 5']",
        },
        {
            trigger: "a[id=review-tab]:contains(Reviews):not(:contains(1))",
            run: "click",
        },
        {
            trigger: "span:contains(Add Review)",
            run: "click",
        },
        {
            trigger: ".modal.modal_shown.show div.o_portal_chatter_composer textarea",
            run: "edit Second review",
        },
        {
            trigger: ".modal.modal_shown .modal-body i.fa.fa-star:eq(2)",
            run: "click",
        },
        {
            trigger:
                ".modal.modal_shown.show button.o_portal_chatter_composer_btn:contains(Post review)",
            run: "click",
        },
        {
            trigger: ".o_wslides_course_header .o_website_rating_static[title='3 stars on 5']",
        },
        {
            trigger: "a[id=review-tab]:contains(Reviews (1))",
            run: "click",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:contains(Second review) .o_website_rating_static[title='3 stars on 5']",
        },
        {
            trigger: "span:contains(Edit Review)",
            run: "click",
        },
        {
            trigger: "div.o_portal_chatter_composer textarea:value(Second review)",
            run: "edit Second review is edited in rating composer",
        },
        {
            trigger: ".modal.modal_shown .modal-body i.fa.fa-star:eq(1)",
            run: "click",
        },
        {
            trigger:
                ".modal.modal_shown.show button.o_portal_chatter_composer_btn:contains(Update review)",
            run: "click",
        },
        {
            trigger: ".o_wslides_course_header .o_website_rating_static[title='2 stars on 5']",
        },
        {
            trigger: "a[id=review-tab]:contains(Reviews (1))",
            run: "click",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:contains(Second review is edited in rating composer) .o_website_rating_static[title='2 stars on 5']",
            run: "hover && click #chatterRoot:shadow .o-mail-Message [title='Edit']",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message .o-mail-Composer-input",
            run: "edit Second review is edited in message composer",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message .o-mail-Composer-mainActions button[title='More Actions']",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .dropdown-item:contains('Attach Files')",
            async run() {
                const text = new File(["test"], "test.txt", { type: "text/plain" });
                await inputFiles(".o-mail-Message .o_input_file", [text], {
                    target: document.querySelector("#chatterRoot").shadowRoot,
                });
            },
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message .o-mail-Composer .o-mail-AttachmentContainer:not(.o-isUploading):contains(test.txt)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message a:contains(save)",
            run: "click",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:contains('Second review is edited in message composer')",
        },
        {
            trigger: "span:contains(Edit Review)",
            run: "click",
        },
        {
            trigger:
                "div.o_portal_chatter_composer textarea:value(Second review is edited in message composer)",
            run: "edit Second review is editable in rating composer after editing in message composer.",
        },
        {
            trigger:
                "div.o_portal_chatter_composer .o_portal_chatter_attachment a:contains(test.txt)",
        },
        {
            trigger:
                ".modal.modal_shown.show button.o_portal_chatter_composer_btn:contains(Update review)",
            run: "click",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:contains(Second review is editable in rating composer after editing in message composer)",
            run: "hover && click #chatterRoot:shadow .o-mail-Message [title='Delete']",
        },
        {
            trigger: "#chatterRoot:shadow button:contains(Delete)",
            run: "click",
        },
        {
            trigger: "span:contains(Add Review)",
            run: "click",
        },
        {
            trigger: ".modal.modal_shown.show .o-mail-Composer-starCard:has(input[value='4'])",
        },
    ],
});
