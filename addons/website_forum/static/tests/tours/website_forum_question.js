import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('forum_question', {
    url: '/forum/help-1',
    steps: () => [
    {
        content: "Ask the question in this forum by clicking on the button.",
        trigger: '.o_wforum_ask_btn',
        run: "click",
        expectUnloadPage: true,
    }, {
        content: "Give your question content.",
        trigger: 'input[name=post_name]',
        run: "edit First Question Title",
    },
    {
        trigger: "#wrap:not(:has(input[name=post_name]:value('')))",
    },
    {
        content: "Put your question here.",
        trigger: '.note-editable p',
        run: "editor First Question <p>code here</p>",
    },
    {
        trigger: ".note-editable:not(:has(br))",
    },
    {
        content: "Insert tags related to your question.",
        trigger: '.o_select_menu_toggler',
        run: 'click',
    },
    ...stepUtils.editSelectMenuInput(".o_select_menu_input", "Tag"),
    {
        content: "Create a new tag.",
        trigger: ".o-dropdown-item:contains(Create option)",
        run: "click",
    },
    {
        content: "Check that the 'Tag' tag is added.",
        trigger: ".o_tag_badge_text:contains('Tag')",
    },
    {
        content: "Insert tags related to your question.",
        trigger: ".o_select_menu_toggler",
        run: "click",
    },
    ...stepUtils.editSelectMenuInput(".o_select_menu_input", "tag, test tag"),
    {
        content: "Create multiple new tags.",
        trigger: ".o-dropdown-item:contains(Create option)",
        run: "click",
    },
    {
        content: "Check that the 'tag' tag is added.",
        trigger: ".o_tag_badge_text:contains('tag')",
    },
    {
        content: "Check that the 'test tag' tag is added.",
        trigger: ".o_tag_badge_text:contains('test tag')",
    },
    {
        content: "Click to post your question.",
        trigger: 'button:contains("Post")',
        run: "click",
        expectUnloadPage: true,
    }, {
        content: "This page contain new created question.",
        trigger: '#wrap:has(.fa-star)',
    },
    {
        trigger: ".o_wforum_question:contains(marc demo)",
    },
    {
        content: "Close modal once modal animation is done.",
        trigger: ".modal.modal_shown.show:contains(thanks for posting!) button.btn-close",
        run: "click",
    },
    {
        content: "Check that the code still exists as it was written.",
        trigger: 'div.o_wforum_post_content:contains("First Question <p>code here</p>")',
    },
    {
        content: "Open dropdown to edit the post",
        trigger: '.o_wforum_question a#dropdownMenuLink',
        run: "click",
    },
    {
        content: "Click on edit",
        trigger: '.o_wforum_question button:contains("Edit")',
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "Check that the content is the same",
        trigger: 'div.odoo-editor-editable p:contains("First Question <p>code here</p>")',
    },
    {
        content: "Save changes",
        trigger: 'button:contains("Save Changes")',
        run: "click",
        expectUnloadPage: true,
    },
    {
        trigger: "a:contains(\"Reply\").collapsed",
        content: "Click to reply.",
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        content: "Put your answer here.",
        trigger: '.note-editable p',
        run: "editor First Answer",
    },
    {
        trigger: ".note-editable:not(:has(br))",
    },
    {
        content: "Click to post your answer.",
        trigger: 'button:contains("Post Answer")',
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "Close modal once modal animation is done.",
        trigger: ".modal .modal-header button.btn-close",
        run: "click",
    }, {
        content: "Congratulations! You just created and post your first question and answer.",
        trigger: '.o_wforum_validate_toggler',
    },
    {
        content: "Close modal",
        trigger: ".modal_shown .modal-header:contains('Thanks for posting!') button.btn-close",
        run: "click",
    },
    {
        content: "Go to profile page",
        trigger: "aside span:contains('Marc Demo')",
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "Open activity tab",
        trigger: ".o_wprofile_nav_tabs a[href='#activities']",
        run: "click",
    },
    {
        content: "Check that the filter is set to 'Activity' (by default)",
        trigger: "#o_wprofile_forum_activity_filter button:contains('Activity')",
    },
    {
        content: "Check activity: new question",
        trigger:
            "#o_wprofile_forum_activity_tab_activity div:contains('First Question Title') span:contains('New question')",
    },
    {
        content: "Check activity: question edited",
        trigger:
            "#o_wprofile_forum_activity_tab_activity div:contains('First Question Title') span:contains('Question edited')",
    },
    {
        content: "Check activity: new answer",
        trigger:
            "#o_wprofile_forum_activity_tab_activity div:contains('First Question Title') span:contains('New answer')",
    },
    {
        content: "Open dropdown activity filter",
        trigger: "#o_wprofile_forum_activity_filter button",
        run: "click",
    },
    {
        content: "Select activity filter: question",
        trigger: "#o_wprofile_forum_activity_filter a:contains('Questions')",
        run: "click",
    },
    {
        content: "Check that the filter is set to 'Question'",
        trigger: "#o_wprofile_forum_activity_filter button:contains('Questions')",
    },
    {
        content: "Check that one posted question is displayed",
        trigger:
            "#activities #o_wprofile_forum_activity_tab_question a:contains('First Question Title')",
    },
    {
        content: "Search for 'Second'",
        trigger:
            ".o_wprofile_forum_activity_search_question input[name='activity_search_question']",
        run: "edit Second",
    },
    {
        content: "Submit search",
        trigger: ".o_wprofile_forum_activity_search_question button[type='submit']",
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "Check that the posted question is not displayed anymore",
        trigger: "a:not(:has(.modal:contains('First Question Title')))",
    },
    {
        content: "Open dropdown activity filter",
        trigger: "#o_wprofile_forum_activity_filter button",
        run: "click",
    },
    {
        content: "Select activity filter: answer",
        trigger: "#o_wprofile_forum_activity_filter a:contains('Answers')",
        run: "click",
    },
    {
        content: "Check that the filter is set to 'Answers'",
        trigger: "#o_wprofile_forum_activity_filter button:contains('Answers')",
    },
    {
        content: "Check posted answer",
        trigger:
            "#activities #o_wprofile_forum_activity_tab_answer a:contains('Re: First Question Title')",
    },
    {
        content: "Search for 'First'",
        trigger:
            ".o_wprofile_forum_activity_search_answer input[name='activity_search_answer']",
        run: "edit First",
    },
    {
        content: "Submit search",
        trigger: ".o_wprofile_forum_activity_search_answer button[type='submit']",
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "Check that posted answer is still displayed",
        trigger:
            "#activities #o_wprofile_forum_activity_tab_answer div:contains('Re: First Question Title')",
    },
    ],
});
