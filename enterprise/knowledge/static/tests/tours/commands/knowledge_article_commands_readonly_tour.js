/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { embeddedViewPatchFunctions, endKnowledgeTour } from '../knowledge_tour_utils.js';

//------------------------------------------------------------------------------
// UTILS
//------------------------------------------------------------------------------

const embeddedViewPatchUtil = embeddedViewPatchFunctions();

//------------------------------------------------------------------------------
// TOUR STEPS - KNOWLEDGE COMMANDS
//------------------------------------------------------------------------------

registry.category("web_tour.tours").add("knowledge_article_commands_readonly_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            // open the Knowledge App
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
            run: "click",
        },
        {
            trigger: "body",
            run() {
                embeddedViewPatchUtil.before();
            },
        },
        /*
         * EMBED VIEW: /list
         * Checks that a user that has readonly access on an article cannot create items from the item list.
         * Note: this tour follows the 'knowledge_article_commands_tour', so we re-use the list name.
         */
        {
            content: "Check view list has no add button",
            trigger: `[data-embedded="view"]:has(.o_list_view):not(:has(.o_list_button_add))`,
        },
        /*
         * EMBED VIEW: /kanban
         * Checks that a user that has readonly access on an article cannot create items from the item kanban.
         * Note: this tour follows the 'knowledge_article_commands_tour', so we re-use the kanban name.
         */
        {
            content: "Check kaban has no add button",
            trigger: `[data-embedded="view"]:has(.o_kanban_view):not(:has(.o_kanban_quick_add))`,
        },
        {
            trigger: "body",
            run() {
                embeddedViewPatchUtil.after();
            },
        },
        ...endKnowledgeTour(),
    ],
});
