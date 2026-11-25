import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { markup } from "@odoo/owl";

const testPdf =
    "JVBERi0xLjEKJWPDtsO2bW1lbnQKMSAwIG9iago8PC9UeXBlIC9DYXRhbG9nCi9QYWdlcyAyIDAgUgo+PgplbmRvYmoKMiAwIG9iago8PC9UeXBlIC9QYWdlcwovS2lkcyBbMyAwIFJdCi9Db3VudCAxCi9NZWRpYUJveCBbMCAwIDIxMCAyOTddCj4+CmVuZG9iagozIDAgb2JqCjw8L1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovUmVzb3VyY2VzCjw8L0ZvbnQKPDwvRjEKPDwvVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9UaW1lcy1Sb21hbgo+Pgo+Pgo+PgovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwvTGVuZ3RoIDQ4Pj4Kc3RyZWFtCkJUCi9GMSA0OCBUZgo1MCAxMzAgVGQKKFRFU1QpIFRqCkVUCmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDUKMDAwMDAwMDAwMCA2NTUzNSBmCjAwMDAwMDAwMjEgMDAwMDAgbgowMDAwMDAwMDY5IDAwMDAwIG4KMDAwMDAwMDE0OSAwMDAwMCBuCjAwMDAwMDAyOTggMDAwMDAgbgp0cmFpbGVyCjw8L1Jvb3QgMSAwIFIKL1NpemUgNQo+PgpzdGFydHhyZWYKMzgxCiUlRU9G";

registry.category("web_tour.tours").add("slides_tour", {
    steps: () => [
        {
            trigger: "body:has(:iframe .o_wslides_home_main) .o_new_content_container button",
            content: _t("Click here to add content to your website."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: 'button[data-module-xml-id="base.module_website_slides"]',
            content: markup(_t("Select <b>Course</b> to create a new Course and manage it.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "input#name_0",
            content: markup(_t("Give your course an engaging <b>Title</b>.")),
            tooltipPosition: "bottom",
            run: "edit My New Course",
        },
        {
            trigger: 'div[name="description"] div[contenteditable=true]',
            content: markup(_t("Give your course a helpful <b>Description</b>.")),
            tooltipPosition: "bottom",
            run: "editor This course is for advanced users.",
        },
        {
            trigger: "button.btn-primary",
            content: markup(_t("Click on the <b>Save</b> button to create your first course.")),
            run: "click",
        },
        {
            trigger: ":iframe .o_wslides_js_slide_section_add",
            content: markup(
                _t(
                    "Congratulations, your course has been created, but there isn't any content yet. First, let's add a <b>Section</b> to give your course a structure."
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ":iframe #section_name",
            content: markup(
                _t("A good course has a structure. Pick a name for your first <b>Section</b>.")
            ),
            tooltipPosition: "bottom",
            run: "edit My First Section",
        },
        {
            trigger: ':iframe button.btn-primary:contains("Save")',
            content: markup(_t("Click <b>Save</b> to create it.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ":iframe:has(.o_wslides_js_category_delete) .o_wslides_course_main a.btn-primary.o_wslides_js_slide_upload",
            content: markup(
                _t(
                    "Your first section is created, now it's time to add lessons to your course. Click on <b>Add Content</b> to upload a document, create an article or link a video."
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ':iframe a[data-slide-category="document"]',
            content: markup(_t("First, let's add a <b>Document</b>. It has to be a .pdf file.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ":iframe input#upload",
            isActive: ["manual"],
            content: markup(_t("Choose a <b>File</b> on your computer.")),
            run: "click",
        },
        {
            trigger: ":iframe input#upload",
            isActive: ["auto"],
            async run({ anchor }) {
                const blob = await (await fetch(`data:application/pdf;base64,${testPdf}`)).blob();
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(new File([blob], "Exercise.pdf", { type: blob.type }));
                anchor.files = dataTransfer.files;
                anchor.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            trigger: ":iframe input#name:value(Exercise)",  // Waiting for file process.
            isActive: ["auto"],
        },
        {
            trigger: ":iframe input#name",
            content: markup(
                _t(
                    "The <b>Title</b> of your lesson is autocompleted but you can change it if you want.</br>A <b>Preview</b> of your file is available on the right side of the screen."
                )
            ),
            run: "click",
        },
        {
            trigger: ":iframe input#duration",
            content: markup(
                _t(
                    "The <b>Duration</b> of the lesson is based on the number of pages of your document. You can change this number if your attendees will need more time to assimilate the content."
                )
            ),
            run: "click",
        },
        {
            trigger: ":iframe button.o_w_slide_upload_published",
            content: markup(
                _t("<b>Save & Publish</b> your lesson to make it available to your attendees.")
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ':iframe span.badge:contains("New")',
            content: markup(
                _t(
                    'Congratulations! Your first lesson is available. Let\'s see the options available here. The tag "<b>New</b>" indicates that this lesson was created less than 7 days ago.'
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ':iframe a[name="o_wslides_list_slide_add_quizz"]',
            isActive: ["manual"],
            content: markup(
                _t(
                    "If you want to be sure that attendees have understood and memorized the content, you can add a Quiz on the lesson. Click on <b>Add Quiz</b>."
                )
            ),
            run: "click",
        },
        {
            // "Add Quizz" only shows on CSS :hover, which synthetic pointer events don't trigger. Clicking on the invisible element.
            trigger: ':iframe a[name="o_wslides_list_slide_add_quizz"]:not(:visible)',
            isActive: ["auto"],
            run: "click",
        },
        {
            trigger: ':iframe .o_wslides_quiz_question input[name="question-name"]',
            content: markup(_t("Enter your <b>Question</b>. Be clear and concise.")),
            tooltipPosition: "left",
            run: "edit A Question",
        },
        {
            trigger: ":iframe input.o_wslides_js_quiz_answer_value",
            content: markup(_t("Enter at least two possible <b>Answers</b>.")),
            tooltipPosition: "left",
            run: "edit First answer",
        },
        {
            trigger: ":iframe .o_wslides_js_quiz_answer:nth-child(2) input.o_wslides_js_quiz_answer_value",
            content: markup(_t("Enter a second <b>Answer</b>.")),
            tooltipPosition: "left",
            run: "edit Second answer",
        },
        {
            trigger: ":iframe a.o_wslides_js_quiz_is_correct label",
            content: markup(_t("Mark the correct answer by checking the <b>correct</b> mark.")),
            tooltipPosition: "right",
            run: "click",
        },
        {
            trigger: ":iframe i.o_wslides_js_quiz_comment_answer:last",
            content: markup(
                _t(
                    "You can add <b>comments</b> on answers. This will be visible with the results if the user select this answer."
                )
            ),
            tooltipPosition: "right",
            run: "click",
        },
        {
            trigger: ":iframe a.o_wslides_js_quiz_validate_question",
            content: markup(_t("<b>Save</b> your question.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            trigger: ":iframe .o_wslides_js_lesson_quiz_submit:contains('Check your answers'):visible",  // Wait for the save.
            isActive: ["auto"],
        },
        {
            trigger: ":iframe .o_wslides_course_nav li.breadcrumb-item:nth-child(2) a",
            content: markup(_t("Click on your <b>Course</b> to go back to the table of content.")),
            tooltipPosition: "top",
            run: "click",
        },
        {
            // Wait for correct page and publish button.
            trigger: "body:has(:iframe .o_wslides_course_main) .o_website_edit_in_backend:contains(Course)",
            isActive: ["auto"],
        },
        {
            trigger: "body:has(:iframe .o_wslides_course_main) .o_menu_systray_item.o_website_publish_container a",
            content: markup(_t("Once you're done, don't forget to <b>Publish</b> your course.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ":iframe a.o_wslides_js_slides_list_slide_link",
            content: markup(
                _t(
                    "Congratulations, you've created your first course.<br/>Click on the title of this content to see it in fullscreen mode."
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ":iframe .o_wslides_fs_toggle_sidebar",
            content: markup(_t("Finally you can click here to enjoy your content in fullscreen")),
            tooltipPosition: "bottom",
            run: "click",
        },
    ]
});
