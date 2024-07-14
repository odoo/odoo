/** @odoo-module */

import { registry } from "@web/core/registry";
import { appendArticleLink, endKnowledgeTour } from '../knowledge_tour_utils.js';
import { stepUtils } from "@web_tour/tour_service/tour_utils";


registry.category("web_tour.tours").add('knowledge_article_command_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    // open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, ...appendArticleLink('[name="body"]', "EditorCommandsArticle"),
{ // wait for the block to appear in the editor
    trigger: '.o_knowledge_behavior_type_article:contains("EditorCommandsArticle")',
    run: 'click',
}, { // check that the view switched to the corresponding article while keeping the breadcrumbs history
    trigger: '.o_knowledge_header:has(.o_breadcrumb_article_name_container:contains("EditorCommandsArticle")):has(.breadcrumb-item > a:contains("EditorCommandsArticle"))'
}, ...endKnowledgeTour()
]});

const composeBody = '.modal-dialog:contains(Compose Email) [name="body"]';
registry.category("web_tour.tours").add('knowledge_article_command_dialog_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    // open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, { // open the chatter
    trigger: '.btn-chatter',
}, { // open the message editor
    trigger: '.o-mail-Chatter-sendMessage:not([disabled=""])',
}, { // open the full composer
    trigger: "button[aria-label='Full composer']",
}, ...appendArticleLink(`${composeBody}`, 'EditorCommandsArticle'), { // wait for the block to appear in the editor
    trigger: `${composeBody} .o_knowledge_behavior_type_article:contains("EditorCommandsArticle")`,
    run: () => {},
}, ...appendArticleLink(`${composeBody}`, 'LinkedArticle', 1), { // wait for the block to appear in the editor, after the previous one
    trigger: `${composeBody} .odoo-editor-editable > p > a:nth-child(2).o_knowledge_behavior_type_article:contains("LinkedArticle")[contenteditable="false"]`,
    run: () => {},
}, { // verify that the first block is still there and contenteditable=false
    trigger: `${composeBody} .odoo-editor-editable > p > a:nth-child(1).o_knowledge_behavior_type_article:contains("EditorCommandsArticle")[contenteditable="false"]`,
    run: () => {},
}, { // send the message
    trigger: '.o_mail_send',
}, {
    trigger: '.o_widget_knowledge_chatter_panel .o-mail-Thread .o-mail-Message-body > p > a:nth-child(1).o_knowledge_behavior_type_article:contains("EditorCommandsArticle")',
    run: () => {},
}, {
    trigger: '.o_widget_knowledge_chatter_panel .o-mail-Thread .o-mail-Message-body > p > a:nth-child(2).o_knowledge_behavior_type_article:contains("LinkedArticle")',
    run: () => {},
}, ...endKnowledgeTour()
]});
