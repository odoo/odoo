/** @odoo-module */

import {
    answerThreadSteps,
    createNewCommentSteps,
    endKnowledgeTour,
    resolveCommentSteps
} from './knowledge_tour_utils.js';
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category('web_tour.tours').add('knowledge_article_thread_main_tour', {
    test: true,
    url: '/web',
    steps: () => [
        stepUtils.showAppsMenuItem(), {
        // Open Knowledge App
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
        }, {
            trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Sepultura")'
        },
        ...createNewCommentSteps(),
        { // Opens the edition of the comment box
            trigger: '.o_knowledge_comment_box, .o_knowledge_comment_box img',
            run: 'click'
        }, {
            trigger: '.o-mail-Composer-input, .o_knowledge_comments_popover',
            run: () => {}
        },
        ...answerThreadSteps('Brand New Comment'),
        ...endKnowledgeTour()
    ]
});

registry.category('web_tour.tours').add('knowledge_article_thread_answer_comment_tour', {
    test: true,
    url: '/web',
    steps: () => [
        stepUtils.showAppsMenuItem(), {
        // Open Knowledge App
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
        },
        {
            trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Sepultura")'
        },
        ...answerThreadSteps(),
        ...endKnowledgeTour()
    ]
});

registry.category('web_tour.tours').add('knowledge_article_thread_resolve_comment_tour', {
    test: true,
    url: '/web',
    steps: () => [
        stepUtils.showAppsMenuItem(), {
        // Open Knowledge App
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
        }, {
            trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Sepultura")'
        }, { // Opens the edition of the comment box
            trigger: '.o_knowledge_comment_box, .o_knowledge_comment_box img',
            run: 'click'
        }, {
            trigger: '.o-mail-Composer-input, .o_knowledge_comments_popover',
            run: () => {}
        },
        ...resolveCommentSteps(), { // Checks that the box is indeed removed from the DOM
            trigger: '.o_widget_knowledge_comments_handler div:not( .o_knowledge_comment_box)',
            run: () => {}
        },
        ...endKnowledgeTour()
    ]
});

registry.category('web_tour.tours').add('knowledge_article_thread_panel_tour', {
    test: true,
    url:'/web',
    steps: () => [
        stepUtils.showAppsMenuItem(), { // Open Knowledge App
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
        }, {
            trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Sepultura")'
        }, { //Opens the panel
            trigger: '.btn-comments'
        }, { //Checks panel is loaded
            trigger: '.o_knowledge_comments_panel',
            run: () => {}
        }, {
            trigger: '.o_knowledge_comments_panel .o_knowledge_comment_box'
        },
        ...answerThreadSteps(),
        ...resolveCommentSteps(),
        { // Open resolved mode
            trigger: '.o_knowledge_comments_panel select',
            run: 'text resolved'
        }, {
            trigger: '.o_knowledge_comment_resolved',
        }, // You can answer on resolved threads
        ...answerThreadSteps('This should be resolved here'),
        ...endKnowledgeTour()
    ]
});
