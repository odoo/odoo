odoo.define('website_slides.slides_tour', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;

var tour = require('web_tour.tour');

tour.register('slides_tour', {
    url: '/slides',
}, [{
    trigger: '#new-content-menu > a',
    content: _t("Welcome on your course's home page. It's still empty for now. Click on \"<b>New</b>\" to write your first course."),
    position: 'bottom',
}, {
    trigger: 'a[data-action="new_slide_channel"]',
    content: _t("Select <b>Course</b> to create it and manage it."),
    position: 'bottom',
    width: 210,
}, {
    trigger: 'input[name="name"]',
    content: _t("Give your course an engaging <b>Title</b>."),
    position: 'bottom',
    width: 280,
    run: 'text My New Course',
}, {
    trigger: 'textarea[name="description"]',
    content: _t("Give your course a helpful <b>Description</b>."),
    position: 'bottom',
    width: 300,
    run: 'text This course is for advanced users.',
}, {
    trigger: 'button.btn-primary',
    content: _t("Click on the <b>Create</b> button to create your first course."),
}, {
    trigger: '.o_wslides_js_slide_section_add',
    content: _t("Congratulations, your course has been created, but there isn't any content yet. First, let's add a <b>Section</b> to give your course a structure."),
    position: 'bottom',
}, {
    trigger: 'input[name="name"]',
    content: _t("A good course has structure and a table of content. Your first section will be the <b>Introduction</b>."),
    position: 'bottom',
}, {
    trigger: 'button.btn-primary',
    content: _t("Click on <b>Save</b> to apply changes."),
    position: 'bottom',
    width: 260,
}, {
    trigger: 'a.btn-primary.o_wslides_js_slide_upload',
    content: _t("Your first section is created, now it's time to add lessons to your course. Click on <b>Add Content</b> to upload a document, create a web page or link a video."),
    position: 'bottom',
}, {
    trigger: 'a[data-slide-type="presentation"]',
    content: _t("First, let's add a <b>Presentation</b>. It can be a .pdf or an image."),
    position: 'bottom',
}, {
    trigger: 'input#upload',
    content: _t("Choose a <b>File</b> on your computer."),
}, {
    trigger: 'input#name',
    content: _t("The <b>Title</b> of your lesson is autocompleted but you can change it if you want.</br>A <b>Preview</b> of your file is available on the right side of the screen."),
}, {
    trigger: 'input#duration',
    content: _t("The <b>Duration</b> of the lesson is based on the number of pages of your document. You can change this number if your attendees will need more time to assimilate the content."),
}, {
    trigger: 'button.o_w_slide_upload_published',
    content: _t("<b>Save & Publish</b> your lesson to make it available to your attendees."),
    position: 'bottom',
    width: 285,
}, {
    trigger: 'span.badge-info:contains("New")',
    content: _t("Congratulations! Your first lesson is available. Let's see the options available here. The tag \"<b>New</b>\" indicates that this lesson was created less than 7 days ago."),
    position: 'bottom',
}, {
    trigger: 'a[name="o_wslides_list_slide_add_quizz"]',
    extra_trigger: '.o_wslides_slides_list_slide:hover',
    content: _t("If you want to be sure that attendees have understood and memorized the content, you can add a Quiz on the lesson. Click on <b>Add Quiz</b>."),
}, {
    trigger: 'input[name="question-name"]',
    content: _t("Enter your <b>Question</b>. Be clear and concise."),
    position: 'left',
    width: 330,
}, {
    trigger: 'input.o_wslides_js_quiz_answer_value',
    content: _t("Enter at least two possible <b>Answers</b>."),
    position: 'left',
    width: 290,
}, {
    trigger: 'a.o_wslides_js_quiz_is_correct',
    content: _t("Mark the correct answer by checking the <b>correct</b> mark."),
    position: 'right',
    width: 230,
}, {
    trigger: 'i.o_wslides_js_quiz_comment_answer:last',
    content: _t("You can add <b>comments</b> on answers. This will be visible with the results if the user select this answer."),
    position: 'right',

}, {
    trigger: 'a.o_wslides_js_quiz_validate_question',
    content: _t("<b>Save</b> your question."),
    position: 'left',
    width: 170,
}, {
    trigger: 'li.breadcrumb-item:nth-child(2)',
    content: _t("Click on your <b>Course</b> to go back to the table of content."),
    position: 'top',
}, {
    trigger: 'label.js_publish_btn',
    content: _t("Once you're done, don't forget to <b>Publish</b> your course."),
    position: 'bottom',
}, {
    trigger: 'a.o_wslides_js_slides_list_slide_link',
    content: _t("Congratulations, you've created your first course.<br/>Click on the title of this content to see it in fullscreen mode."),
    position: 'bottom',
}]);

});
