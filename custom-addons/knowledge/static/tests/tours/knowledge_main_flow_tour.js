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

import { dragAndDropArticle, endKnowledgeTour, makeVisible } from '@knowledge/../tests/tours/knowledge_tour_utils';
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('knowledge_main_flow_tour', {
    test: true,
    url: '/web',
    steps: () => [stepUtils.showAppsMenuItem(), {
    // open Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, {
    // click on the main "New" action
    trigger: '.o_knowledge_header .btn:contains("New")',
}, {
    // check that the article is correctly created (private section)
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable:focus',
    run: () => {},
}, {
    trigger: '.note-editable.odoo-editor-editable h1',
    run: 'text My Private Article',  // modify the article content
}, {
    trigger: 'section[data-section="workspace"]',
    run: () => {
        // force the create button to be visible (it's only visible on hover)
        makeVisible('section[data-section="workspace"] .o_section_create');
    },
}, {
    // create an article in the "Workspace" section
    trigger: 'section[data-section="workspace"] .o_section_create',
}, {
    // check that the article is correctly created (workspace section), and that the previous
    // article has been renamed using its title (first h1 in body).
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
    extra_trigger: 'section[data-section="private"] .o_article .o_article_name:contains("My Private Article")',
    run: () => {},
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable:focus',
    run: () => {},
}, {
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text My Workspace Article',  // modify the article name
}, {
    trigger: '.note-editable.odoo-editor-editable',
    run: 'text Content of My Workspace Article',  // modify the article content
}, {
    trigger: '.o_article:contains("My Workspace Article")',
    run: () => {
        // force the create button to be visible (it's only visible on hover)
        $('.o_article:contains("My Workspace Article") a.o_article_create').css('display', 'block');
    },
}, {
    // create child article
    trigger: '.o_article:contains("My Workspace Article") a.o_article_create',
}, {
    // check that the article is correctly created (workspace section)
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable:focus',
    run: () => {},
}, {
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Child Article 1',  // modify the article name
}, {
    trigger: '.o_article:contains("My Workspace Article")',
}, {
    // create child article (2)
    trigger: '.o_article:contains("My Workspace Article") a.o_article_create',
}, {
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable:focus',
    run: () => {},
}, {
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Child Article 2',  // modify the article name
}, {
    // move child article 2 above child article 1
    trigger: '.o_article_handle:contains("Child Article 2")',
    run: () => {
        dragAndDropArticle(
            $('.o_article_handle:contains("Child Article 2")'),
            $('.o_article_handle:contains("Child Article 1")'),
        );
    },
}, {
    // verify that the move was done
    trigger: '.o_article:has(.o_article_name:contains("My Workspace Article")) ul > :eq(0):contains("Child Article 2")',
    run: () => {},
}, {
    // go back to main workspace article
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("My Workspace Article")',
}, {
    trigger: '.o_knowledge_editor:contains("Content of My Workspace Article")',
    run: () => {},  // wait for article to be correctly loaded
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable:focus',
    run: () => {},
}, {
    // open the share dropdown
    trigger: '.o_knowledge_header .btn:contains("Share")',
}, {
    // click on 'Invite'
    trigger: '.o_knowledge_share_panel .btn:contains("Invite")',
}, {
    // Type the invited person's name
    trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
    run: 'text micheline@knowledge.com',
}, {
    // Open the simplified create form view
    trigger: '.o-autocomplete--dropdown-menu .o_m2o_dropdown_option_create_edit a',
    run: 'click',
}, {
    // Give an email address to the partner
    trigger: '.o_field_widget[name=email] input',
    run: 'text micheline@knowledge.com',
}, {
    // Save the new partner
    trigger: '.o_form_button_save',
}, {
    // Submit the invite wizard
    trigger: 'button:contains("Invite")',
    extra_trigger: '.o_field_tags span.o_badge_text',
}, {
    // add to favorite
    trigger: '.o_knowledge_toggle_favorite',
}, {
    // check article was correctly added into favorites
    trigger: 'section[data-section="favorites"] .o_article .o_article_name:contains("My Workspace Article")',
    run: () => {},
}, {
    // open the share dropdown
    trigger: '.o_knowledge_header .btn:contains("Share")',
}, {
    // open the share dropdown
    trigger: '.o_member_email:contains("micheline@knowledge.com")',
    in_modal: false,
    run: () => {},
}, {
    // go back to private article
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("My Private Article")',
}, {
    trigger: '.o_knowledge_editor:contains("My Private Article")',
    run: () => {},  // wait for article to be correctly loaded
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable:focus',
    run: () => {},
}, {
    // add to favorite
    trigger: '.o_knowledge_toggle_favorite',
}, {
    // wait for the article to be registered as favorited
    trigger: '.o_knowledge_toggle_favorite .fa-star',
    run: () => {},
}, {
    // move private article above workspace article in the favorite section
    trigger: 'section[data-section="favorites"] .o_article_handle:contains("My Private Article")',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="favorites"] .o_article_handle:contains("My Private Article")'),
            $('section[data-section="favorites"] .o_article_handle:contains("My Workspace Article")'),
        );
    },
}, {
    // verify that the move was done
    trigger: 'section[data-section="favorites"] ul > :eq(0):contains("My Private Article")',
    run: () => {},
}, {
    // go back to main workspace article
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("My Workspace Article")',
}, {
    trigger: ':contains("Content of My Workspace Article")',
    run() {},
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable:focus',
    run: () => {},
}, {
    // click on the main "New" action
    trigger: '.o_knowledge_header .btn:contains("New")',
}, {
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("Untitled")',
    run: () => {}, // check that the article is correctly created (private section)
}, {
    // check the autofocus
    trigger: '.note-editable.odoo-editor-editable:focus',
    run: () => {},
}, {
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Article to be moved',  // modify the article name
}, {// move article
    trigger: 'a#dropdown_tools_panel',
    run: 'click'
}, {
    trigger: '.btn-move',
    run: 'click',
}, {
    trigger: '.o_select_menu_item:contains("Article 3")',
    run: 'click',
}, {
    trigger: '.o_select_menu_toggler_slot:contains("Article 3")',
    run: () => {},
}, {
    trigger: '.modal-content .btn-primary:contains("Move Article")',
    run: 'click',
}, {
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Article to be moved")',
    run: 'click'
}, {
    // open the trash
    trigger: '.o_knowledge_sidebar_trash div[role="button"]',
}, {
    // verify that the trash list has been opened correctly and that items are correctly ordered
    trigger: '.o_data_row:first .o_data_cell[name="display_name"]:contains("Article 2")',
    extra_trigger: '.o_breadcrumb .active:contains("Trash")',
    run: () => {},
}, ...endKnowledgeTour()
]});
