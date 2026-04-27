/** @odoo-module */

import { registry } from "@web/core/registry";
import { insertText } from "@web/../tests/utils";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { endKnowledgeTour } from "./knowledge_tour_utils.js";
import { setSelection, boundariesIn } from "@web_editor/js/editor/odoo-editor/src/utils/utils";

const addAnswerComment = (commentText) => [{
    trigger: '.o-mail-Composer-input',
    run: async () => {
        await insertText('.o-mail-Composer-input', commentText);
    }
}, {
    // Send comment
    trigger: '.o-mail-Composer-send:enabled',
    run: "click",
}, {
    trigger: `.o-mail-Thread :contains(${commentText})`,
}];

registry.category('web_tour.tours').add('knowledge_article_comments', {
    url: '/odoo',
    steps: () => [
        stepUtils.showAppsMenuItem(), { // Open Knowledge App
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
            run: "click",
        }, {
            trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Sepultura")',
            run: "click",
        }, {
            trigger: '.o_knowledge_comment_box[data-thread-id], .o_knowledge_comment_small_ui img',
            run: "click",
        }, {
            trigger: '.o-mail-Thread :contains("Marc, can you check this?")',
        },
        ...addAnswerComment("Sure thing boss, all done!"),
        {
            content: "Hover on first message to make actions visible and click on it",
            trigger: ".o-mail-Message-core:first",
            run: "hover && click .o-mail-Message-actions:first",
        },
        {
            content: "Resolve Thread",
            trigger: ".o-mail-Message-actions:first button[name=closeThread]",
            run: "click",
        },
        {
            content: "Wait for the composer to be fully closed",
            trigger: "body:not(:has(.o-mail-Thread))",
        },
        {
            content: "Select some text in the first paragraph",
            trigger: ".note-editable p.o_knowledge_tour_first_paragraph",
            run: function () {
                setSelection(...boundariesIn(this.anchor));
            },
        }, { // Trigger comment creation with the editor toolbar
            trigger: '.o-we-toolbar button[name="comments"]',
            run: "click",
        }, {
            trigger: '.o_knowledge_comments_popover .o-mail-Composer-input',
            run: async () => {
                await insertText('.o-mail-Composer-input', 'My Knowledge Comment');
            }
        }, { // Send comment
            trigger: '.o_knowledge_comments_popover .o-mail-Composer-send:enabled',
            run: "click",
        }, { // Wait for the comment to be fully created
            trigger: ".note-editable p.o_knowledge_tour_first_paragraph a:not([data-id='undefined']):not(:visible)",
        }, {
            trigger: '.o_knowledge_comment_box[data-thread-id] .o_knowledge_comment_small_ui img',
        }, { // Open the comments panel
            trigger: '.btn-comments',
            run: "click",
        }, { // Panel loads un-resolved messages
            trigger: '.o-mail-Thread :contains("My Knowledge Comment")',
        }, { // Switch to "resolved" mode
            trigger: '.o_knowledge_comments_panel select',
            run: "select resolved",
        }, { // Panel loads resolved messages
            trigger: '.o-mail-Thread :contains("Sure thing boss, all done!")',
        }, { // Open the comment to enable replies
            trigger: '.o_knowledge_comment_box',
            run: "click",
        },
        // Add an extra reply to the resolved comment
        ...addAnswerComment("Oops forgot to mention, will be done in task-112233"),
        ...endKnowledgeTour()
    ]
});
