/** @odoo-module */

/**
 * Global Knowledge flow tour.
 * Features tested:
 * - Create an article
 * - Change its title / content
 * - Share an article with a created partner
 * - Create 2 children articles and invert their order
 * - Favorite 2 different articles and invert their order in the favorite section
 */

import {
    dragAndDropArticle,
    endKnowledgeTour,
} from "@knowledge/../tests/tours/knowledge_tour_utils";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('knowledge_main_flow_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    // open Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
    run: "click",
}, {
    // click on the main "New" action
    trigger: '.o_knowledge_header .btn:contains("New")',
    run: "click",
}, {
    // check that the article is correctly created (private section)
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("Untitled")',
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable',
    run: function () {
        const selection = document.getSelection();
        if (!this.anchor.contains(selection.anchorNode)) {
            throw new Error("The autofocus doesn't work");
        }
    }
}, {
    trigger: '.note-editable.odoo-editor-editable h1',
    run: "editor My Private Article",  // modify the article content
},
{
    trigger: 'section[data-section="workspace"]',
    run: "hover && click section[data-section=workspace] .o_section_create",
},
{
    trigger:
        'section[data-section="private"] .o_article .o_article_name:contains("My Private Article")',
},
{
    // check that the article is correctly created (workspace section), and that the previous
    // article has been renamed using its title (first h1 in body).
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable',
    run: function () {
        const selection = document.getSelection();
        if (!this.anchor.contains(selection.anchorNode)) {
            throw new Error("The autofocus doesn't work");
        }
    }
}, {
    trigger: '.o_hierarchy_article_name > input',
    run: 'edit My Workspace Article && click body',  // modify the article name
}, {
    trigger: '.note-editable.odoo-editor-editable',
    run: "editor Content of My Workspace Article",  // modify the article content
}, {
    trigger: '.o_article:contains("My Workspace Article")',
    run: "hover && click .o_article:contains(My Workspace Article) a.o_article_create",
}, {
    // check that the article is correctly created (workspace section)
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable',
    run: function () {
        const selection = document.getSelection();
        if (!this.anchor.contains(selection.anchorNode)) {
            throw new Error("The autofocus doesn't work");
        }
    }
}, {
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Child Article 1 && click body",  // modify the article name
}, {
    trigger: '.o_article:contains("My Workspace Article")',
    run: "hover && click .o_article:contains(My Workspace Article) a.o_article_create",
}, {
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable',
    run: function () {
        const selection = document.getSelection();
        if (!this.anchor.contains(selection.anchorNode)) {
            throw new Error("The autofocus doesn't work");
        }
    }
}, {
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Child Article 2 && click body",  // modify the article name
}, {
    // move child article 2 above child article 1
    trigger: '.o_article_handle:contains("Child Article 2")',
    run: () => {
        dragAndDropArticle(
            '.o_article_handle:contains("Child Article 2")',
            '.o_article_handle:contains("Child Article 1")',
        );
    },
}, {
    // verify that the move was done
    trigger: '.o_article:has(.o_article_name:contains(My Workspace Article)) ul li:first:contains(Child Article 2)',
}, {
    // go back to main workspace article
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("My Workspace Article")',
    run: "click",
}, {
    trigger: '.o_knowledge_editor:contains("Content of My Workspace Article")',
  // wait for article to be correctly loaded
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable',
    run: function () {
        const selection = document.getSelection();
        if (!this.anchor.contains(selection.anchorNode)) {
            throw new Error("The autofocus doesn't work");
        }
    }
}, {
    // open the share dropdown
    trigger: '.o_knowledge_header .btn:contains("Share")',
    run: "click",
        },
        {
            content: "click on 'Invite'",
            trigger: '.o_knowledge_share_panel .btn:contains("Invite")',
            run: "click",
        },
        {
            content: "Type the invited person's name",
            trigger: ".o_field_many2many_tags_email[name=partner_ids] input",
            run: "edit micheline@knowledge.com",
        },
        {
            content: "Open the simplified create form view",
            trigger: ".o-autocomplete--dropdown-menu .o_m2o_dropdown_option_create_edit a",
            run: "click",
        },
        {
            content: "Give an email address to the partner",
            trigger: ".modal .o_field_widget[name=email] input",
            run: "edit micheline@knowledge.com",
        },
        {
            content: "Save the new partner",
            trigger: ".modal .o_form_button_save:contains(save & close)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal:contains(create recipients)))",
        },
        {
            trigger: ".modal .o_field_tags span.o_badge_text",
        },
        {
            content: "Submit the invite wizard",
            trigger: ".modal button:contains(Invite)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal:contains(invite people)))",
        },
        {
    // add to favorite
    trigger: '.o_knowledge_toggle_favorite',
    run: "click",
}, {
    // check article was correctly added into favorites
    trigger: 'section[data-section="favorites"] .o_article .o_article_name:contains("My Workspace Article")',
}, {
    // open the share dropdown
    trigger: '.o_knowledge_header .btn:contains("Share")',
    run: "click",
}, {
    // open the share dropdown
    trigger: '.o_member_email:contains("micheline@knowledge.com")',
}, {
    // go back to private article
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("My Private Article")',
    run: "click",
}, {
    trigger: '.o_knowledge_editor:contains("My Private Article")',
  // wait for article to be correctly loaded
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable',
    run: function () {
        const selection = document.getSelection();
        if (!this.anchor.contains(selection.anchorNode)) {
            throw new Error("The autofocus doesn't work");
        }
    }
}, {
    // add to favorite
    trigger: '.o_knowledge_toggle_favorite',
    run: "click",
}, {
    // wait for the article to be registered as favorited
    trigger: '.o_knowledge_toggle_favorite .fa-star',
}, {
    // move private article above workspace article in the favorite section
    trigger: 'section[data-section="favorites"] .o_article_handle:contains("My Private Article")',
    run: () => {
        dragAndDropArticle(
            'section[data-section="favorites"] .o_article_handle:contains("My Private Article")',
            'section[data-section="favorites"] .o_article_handle:contains("My Workspace Article")',
        );
    },
}, {
    // verify that the move was done
    trigger: 'section[data-section="favorites"] ul li:first:contains(My Private Article)',
}, {
    // go back to main workspace article
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("My Workspace Article")',
    run: "click",
}, {
    trigger: ':contains("Content of My Workspace Article")',
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable',
    run: function () {
        const selection = document.getSelection();
        if (!this.anchor.contains(selection.anchorNode)) {
            throw new Error("The autofocus doesn't work");
        }
    }
}, {
    // click on the main "New" action
    trigger: '.o_knowledge_header .btn:contains("New")',
    run: "click",
}, {
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("Untitled")',
 // check that the article is correctly created (private section)
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable',
    run: function () {
        const selection = document.getSelection();
        if (!this.anchor.contains(selection.anchorNode)) {
            throw new Error("The autofocus doesn't work");
        }
    }
}, {
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Article to be moved && click body",  // modify the article name
}, {// move article
    trigger: 'a#dropdown_tools_panel',
    run: 'click'
}, {
    trigger: '.btn-move',
    run: "click",
}, {
    trigger: '.o_select_menu_item:contains("Article 3")',
    run: "click",
}, {
    trigger: '.o_select_menu_toggler_slot:contains("Article 3")',
}, {
    trigger: '.modal-content .btn-primary:contains("Move Article")',
    run: "click",
}, {
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Article to be moved")',
    run: 'click'
}, {
    // open the trash
    trigger: '.o_knowledge_sidebar_trash div[role="button"]',
    run: "click",
},
{
    trigger: '.o_breadcrumb .active:contains("Trash")',
},
{
    // verify that the trash list has been opened correctly and that items are correctly ordered
    trigger: '.o_data_row:first .o_data_cell[name="display_name"]:contains("Article 2")',
}, ...endKnowledgeTour()
]});
