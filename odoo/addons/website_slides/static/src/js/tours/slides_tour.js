/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import wTourUtils from "@website/js/tours/tour_utils";

import { markup } from "@odoo/owl";

wTourUtils.registerWebsitePreviewTour('slides_tour', {
    url: '/slides',
}, () => [{
    trigger: "body:not(.editor_has_snippets) .o_new_content_container > a",
    content: markup(_t("Welcome on your course's home page. It's still empty for now. Click on \"<b>New</b>\" to write your first course.")),
    consumeVisibleOnly: true,
    position: 'bottom',
}, {
    trigger: 'a[data-module-xml-id="base.module_website_slides"]',
    content: markup(_t("Select <b>Course</b> to create it and manage it.")),
    position: 'bottom',
    width: 210,
}, {
    trigger: 'input#name_0',
    content: markup(_t("Give your course an engaging <b>Title</b>.")),
    position: 'bottom',
    width: 280,
    run: 'text My New Course',
}, {
    trigger: 'div[name="description"] div[contenteditable=true]',
    content: markup(_t("Give your course a helpful <b>Description</b>.")),
    position: 'bottom',
    width: 300,
    run: 'text This course is for advanced users.',
}, {
    trigger: 'button.btn-primary',
    content: markup(_t("Click on the <b>Save</b> button to create your first course.")),
}, {
    trigger: 'iframe .o_wslides_js_slide_section_add',
    content: markup(_t("Congratulations, your course has been created, but there isn't any content yet. First, let's add a <b>Section</b> to give your course a structure.")),
    position: 'bottom',
}, {
    trigger: 'iframe #section_name',
    content: markup(_t("A good course has a structure. Pick a name for your first <b>Section</b>.")),
    position: 'bottom',
}, {
    trigger: 'iframe button.btn-primary',
    content: markup(_t("Click <b>Save</b> to create it.")),
    position: 'bottom',
    width: 260,
}, {
    trigger: 'iframe a.btn-primary.o_wslides_js_slide_upload',
    content: markup(_t("Your first section is created, now it's time to add lessons to your course. Click on <b>Add Content</b> to upload a document, create an article or link a video.")),
    position: 'bottom',
}, {
    trigger: 'iframe a[data-slide-category="document"]',
    content: markup(_t("First, let's add a <b>Document</b>. It has to be a .pdf file.")),
    position: 'bottom',
}, {
    trigger: 'iframe input#upload',
    content: markup(_t("Choose a <b>File</b> on your computer.")),
}, {
    trigger: 'iframe input#name',
    content: markup(_t("The <b>Title</b> of your lesson is autocompleted but you can change it if you want.</br>A <b>Preview</b> of your file is available on the right side of the screen.")),
}, {
    trigger: 'iframe input#duration',
    content: markup(_t("The <b>Duration</b> of the lesson is based on the number of pages of your document. You can change this number if your attendees will need more time to assimilate the content.")),
}, {
    trigger: 'iframe button.o_w_slide_upload_published',
    content: markup(_t("<b>Save & Publish</b> your lesson to make it available to your attendees.")),
    position: 'bottom',
    width: 285,
}, {
    trigger: 'iframe span.badge:contains("New")',
    content: markup(_t("Congratulations! Your first lesson is available. Let's see the options available here. The tag \"<b>New</b>\" indicates that this lesson was created less than 7 days ago.")),
    position: 'bottom',
}, {
    trigger: 'iframe a[name="o_wslides_list_slide_add_quizz"]',
    content: markup(_t("If you want to be sure that attendees have understood and memorized the content, you can add a Quiz on the lesson. Click on <b>Add Quiz</b>.")),
}, {
    trigger: 'iframe input[name="question-name"]',
    content: markup(_t("Enter your <b>Question</b>. Be clear and concise.")),
    position: 'left',
    width: 330,
}, {
    trigger: 'iframe input.o_wslides_js_quiz_answer_value',
    content: markup(_t("Enter at least two possible <b>Answers</b>.")),
    position: 'left',
    width: 290,
}, {
    trigger: 'iframe a.o_wslides_js_quiz_is_correct',
    content: markup(_t("Mark the correct answer by checking the <b>correct</b> mark.")),
    position: 'right',
    width: 230,
}, {
    trigger: 'iframe i.o_wslides_js_quiz_comment_answer:last',
    content: markup(_t("You can add <b>comments</b> on answers. This will be visible with the results if the user select this answer.")),
    position: 'right',

}, {
    trigger: 'iframe a.o_wslides_js_quiz_validate_question',
    content: markup(_t("<b>Save</b> your question.")),
    position: 'left',
    width: 170,
}, {
    trigger: 'iframe li.breadcrumb-item:nth-child(2)',
    content: markup(_t("Click on your <b>Course</b> to go back to the table of content.")),
    position: 'top',
}, {
    trigger: '.o_menu_systray_item a .o_switch',
    content: markup(_t("Once you're done, don't forget to <b>Publish</b> your course.")),
    position: 'bottom',
}, {
    trigger: 'iframe a.o_wslides_js_slides_list_slide_link',
    content: markup(_t("Congratulations, you've created your first course.<br/>Click on the title of this content to see it in fullscreen mode.")),
    position: 'bottom',
}, {
    trigger: 'iframe .o_wslides_fs_toggle_sidebar',
    content: markup(_t("Finally you can click here to enjoy your content in fullscreen")),
    position: 'bottom',
}]);
