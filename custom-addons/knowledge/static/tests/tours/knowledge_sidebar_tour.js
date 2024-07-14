/** @odoo-module */

import { changeInternalPermission, dragAndDropArticle, makeVisible } from '@knowledge/../tests/tours/knowledge_tour_utils';
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";


/**
 * Sidebar tour.
 * Tests sidebar features and responsiveness.
 * Todo: add responsiveness checks from usage of moveArticleDialog
 * when select2 will be replaced (can currently not select options)
 */

registry.category("web_tour.tours").add('knowledge_sidebar_tour', {
    test: true,
    url: '/web',
    steps: () => [stepUtils.showAppsMenuItem(), {
    // Open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
},
// Create a workspace article
{
    // Force the create button to be visible (it's only visible on hover)
    trigger: 'section[data-section="workspace"]',
    run: () => {
        makeVisible('section[data-section="workspace"] .o_section_create');
    },
}, {
    // Create an article in the "Workspace" section
    trigger: 'section[data-section="workspace"] .o_section_create',
}, {
    // Check that the article is created inside the Workspace
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},
}, {
    // Rename the article
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Workspace Article',
}, {
    // Check that the name has been updated in the sidebar
    trigger: '.o_article_active:contains("Workspace Article")',
    run: () => {},
}, {
    // Add content to the article
    trigger: '.note-editable.odoo-editor-editable',
    run: 'text Content of Workspace Article',
},
// Create a private article
{
    // Force the create button to be visible (it's only visible on hover)
    trigger: 'section[data-section="private"]',
    run: () => {
        makeVisible('section[data-section="private"] .o_section_create');
    },
}, {
    // Create an article in the "Private" section
    trigger: 'section[data-section="private"] .o_section_create',
}, {
    // Check that the article is created inside the private section
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("Untitled")',
    run: () => {},
}, {
    // Rename the article
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Private Article',
},
// Create a shared article
{
    // Check that the shared section does not exists
    trigger: '.o_knowledge_tree:not(:has(section[data-section="shared"]))',
    extra_trigger: '.o_article_active:contains("Private Article")',
    run: () => {},
}, {
    // First create a private one
    trigger: 'section[data-section="private"] .o_section_create',
}, {
    // Rename the article
    trigger: '.o_breadcrumb_article_name > input',
    extra_trigger: '.o_article_active:contains("Untitled")',
    run: 'text Shared Article',
}, {
    // Open the share dropdown
    trigger: '.o_knowledge_header .btn:contains("Share")',
}, {
    // Click on 'Invite'
    trigger: '.o_knowledge_share_panel .btn:contains("Invite")',
}, {
    // Type the invited person's name
    trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
    run: 'text henri@knowledge.com',
}, {
    // Open the simplified create form view
    trigger: '.o-autocomplete--dropdown-menu .o_m2o_dropdown_option_create_edit a',
    run: 'click',
}, {
    // Give an email address to the partner
    trigger: '.o_field_widget[name=email] input',
    run: 'text henri@knowledge.com',
}, {
    // Save the new partner
    trigger: '.o_form_button_save',
}, {
    // Submit the invite wizard
    trigger: 'button:contains("Invite")',
    extra_trigger: '.o_field_tags span.o_badge_text',
}, {
    // Check that the article has been added to a new "Shared" section
    trigger: 'section[data-section="shared"]:contains("Shared Article")',
    run: () => {},
},
// Create a child of a workspace article
{
    // Force the create button to be visible (it's only visible on hover)
    trigger: '.o_article:contains("Workspace Article")',
    run: () => {
        $('.o_article:contains("Workspace Article") a.o_article_create').css('display', 'block');
    },
}, {
    // Create a child
    trigger: '.o_article:contains("Workspace Article") a.o_article_create',
}, {
    // Check that the child has been added
    trigger: '.o_article:contains("Workspace Article") .o_article:contains("Untitled")',
    run: () => {},
}, {
    // Rename the article
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Workspace Child',
},
// Create a child of a private article
{
    // Force the create button to be visible (it's only visible on hover)
    trigger: '.o_article:contains("Private Article")',
    run: () => {
        $('.o_article:contains("Private Article") a.o_article_create').css('display', 'block');
    },
}, {
    // Create a child
    trigger: '.o_article:contains("Private Article") a.o_article_create',
}, {
    // Check that the child has been added
    trigger: '.o_article:contains("Private Article") .o_article:contains("Untitled")',
    run: () => {},
}, {
    // Rename the article
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Private Child 1',
},
// Create a child of a shared article
{
    // Force the create button to be visible (it's only visible on hover)
    trigger: '.o_article:contains("Shared Article")',
    run: () => {
        $('.o_article:contains("Shared Article") a.o_article_create').css('display', 'block');
    },
}, {
    // Create a child
    trigger: '.o_article:contains("Shared Article") a.o_article_create',
}, {
    // Check that the child has been added
    trigger: '.o_article:contains("Shared Article") .o_article:contains("Untitled")',
    run: () => {},
}, {
    // Rename the article
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Shared Child',
},
// Open an article by clicking on it
{
    // Click in the sidebar
    trigger: '.o_article_name:contains("Workspace Article")',
}, {
    // Check that article is correctly opened
    trigger: '.note-editable.odoo-editor-editable:contains("Content of Workspace Article")',
    extra_trigger: '.o_article_active:contains("Workspace Article")',
    run: () => {},
},
// Open an article using the searchBox
{
    // Open the CP
    trigger: '#knowledge_search_bar',
}, {
    // Click on an article
    trigger: '.o_command_name:not(.small):contains("Private Article")',
}, {
    // Check article was opened
    trigger: '.o_article_active .o_article_name:contains("Private Article")',
    run: () => {},
}, 
// Open the trash
{
    trigger: '.o_knowledge_sidebar_trash > div[role="button"]',
}, {
    // Check that trash has been opened
    trigger: '.o_last_breadcrumb_item.active:contains("Trash")',
    run: () => {},
}, {
    // Come back to the form view
    trigger: '.breadcrumb-item.o_back_button',
},
// Add/remove an article to/from the favorites
{
    // Make sure the favorite section does not exists
    trigger: '.o_knowledge_tree:not(:has(section[data-section="favorites"]))',
    run: () => {},
}, {
    // Click on the toggleFavorite button
    trigger: 'a.o_knowledge_toggle_favorite',
}, {
    // Check that the article has been added to the added favorite section
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article")',
    run: () => {},
}, {
    // Click on the toggleFavorite button again
    trigger: 'a.o_knowledge_toggle_favorite',
}, {
    // Check that the favorite section has been removed
    trigger: '.o_knowledge_tree:not(:has(section[data-section="favorites"]))',
    extra_trigger: 'a.o_knowledge_toggle_favorite .fa-star-o',
},
// Unfold/Fold favorite article
{
    // Add article to favorite
    trigger: 'a.o_knowledge_toggle_favorite',
}, {
    // Check that favorite is initially folded, and unfold it
    trigger: 'section[data-section="favorites"] .o_article_caret .fa-caret-right',
    extra_trigger: 'section[data-section="favorites"] .o_article:not(:has(.o_article))',
}, {
    // Check that caret changed and that child is displayed
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article") .o_article_name:contains("Private Child 1")',
    extra_trigger: 'section[data-section="favorites"] .o_article_caret .fa-caret-down',
    run: () => {},
}, {
    // Click on the caret again to refold the article
    trigger: 'section[data-section="favorites"] .o_article_caret',
}, {
    // Check that caret changed and that child is hidden again
    trigger: 'section[data-section="favorites"] .o_article:not(:has(.o_article))',
    extra_trigger: 'section[data-section="favorites"] .o_article_caret .fa-caret-right',
    run: () => {},
}, {
    // Check that article in main tree is still unfolded
    trigger: 'section[data-section="private"] .o_article:contains("Private Child 1")',
    run: () => {},
},

// Create a child from the favorite tree
{
    // Force the create button to be visible (it's only visible on hover)
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article")',
    extra_trigger: 'section[data-section="favorites"] .o_article_caret .fa-caret-right',
    run: () => {
        $('section[data-section="favorites"] .o_article:contains("Private Article") a.o_article_create').css('display', 'block');
    },
}, {
    // Create a child
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article") a.o_article_create',
}, {
    // Check that article has been unfolded
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article") .fa-caret-down',
    run: () => {},
}, {
    // Check that previously existing child is displayed
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article") .o_article_name:contains("Private Child 1")',
    run: () => {},
}, {
    // Check that the child has been added in the favorite tree
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article") .o_article_name:contains("Untitled")',
    run: () => {},
}, {
    // Check that the child has been added in the private section
    trigger: 'section[data-section="private"] .o_article:contains("Private Article") .o_article_name:contains("Untitled")',
    run: () => {},
}, {
    // Rename the article
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Private Child 2',
}, {
    // Check that the article has been renamed in the favorite tree
    trigger: 'section[data-section="favorites"] .o_article_name:contains("Private Child 2")',
    run: () => {},
}, {
    // Check that the article has been renamed in the private section
    trigger: 'section[data-section="private"] .o_article_name:contains("Private Child 2")',
    run: () => {},
},
// Fold/unfold an article
{
    // Click on the caret (should be caret down)
    trigger: 'section[data-section="private"] .o_article_caret',
    extra_trigger: 'section[data-section="private"] .o_article_caret .fa-caret-down',
}, {
    // Check that caret changed, and that children are hidden, and that favorite has not been folded
    trigger: 'section[data-section="private"] .o_article:not(:has(.o_article))',
    extra_trigger: 'section[data-section="private"] .o_article_caret .fa-caret-right',
    run: () => {},
}, {
    // Check that favorite has not been folded
    trigger: 'section[data-section="favorites"] .o_article .o_article',
    extra_trigger: 'section[data-section="favorites"] .o_article_handle:contains("Private Article") .fa-caret-down',
}, {
    // Fold favorite article (to later check that unfolding article won't unfold favorite)
    trigger: 'section[data-section="favorites"] .o_article_caret',
}, {
    // Click on the caret again
    trigger: 'section[data-section="private"] .o_article_caret',
}, {
    // Check that articles are shown again
    trigger: 'section[data-section="private"] .o_article .o_article',
    extra_trigger: 'section[data-section="private"] .o_article_caret .fa-caret-down',
    run: () => {},
}, {
    // Check that favorite has not been unfolded
    trigger: 'section[data-section="favorites"] .o_article:not(:has(.o_article))',
    extra_trigger: 'section[data-section="favorites"] .o_article_handle:contains("Private Article") .fa-caret-right',
    run: () => {},
},
// Create a child of a folded article
{
    // Fold article again
    trigger: 'section[data-section="private"] .o_article_caret',
}, {
    trigger: 'section[data-section="private"] .o_article_caret .fa-caret-right',
    run: () => {
        $('section[data-section="private"] .o_article:contains("Private Article") .o_article_create').css('display', 'block');
    }
}, {
    // Click on the create button
    trigger: 'section[data-section="private"] .o_article:contains("Private Article") .o_article_create',
}, {
    // Check that article has been unfolded and that previously existing children are shown
    trigger: 'section[data-section="private"] .o_article .o_article:contains("Private Child 1")',
    extra_trigger: 'section[data-section="private"] .o_article_caret .fa-caret-down',
    run: () => {},
}, {
    // Check that article has been added in both trees
    trigger: 'section[data-section="private"] .o_article .o_article:contains("Untitled")',
    extra_trigger: 'section[data-section="favorites"] .o_article .o_article:contains("Untitled")',
    run: () => {},
}, {
    // Rename the article
    trigger: '.o_breadcrumb_article_name > input',
    run: 'text Private Child 3',
},
// Add a random icon
{
    // Force the add icon button to be visible (it's only visible on hover)
    trigger: '.o_knowledge_add_buttons',
    run: () => {
        makeVisible('.o_knowledge_add_icon');
    },
}, {
    // Click on the "add Icon" button
    trigger: '.o_knowledge_add_icon',
}, {
    // Check that the icon has been updated in the sidenar
    trigger: '.o_knowledge_body div[name="icon"]',
    run: () => {
        const bodyIcon = document.querySelector('.o_knowledge_body div[name="icon"]').innerText;
        const sidebarIcon = document.querySelector('.o_article_active .o_article_emoji').innerText;
        if (bodyIcon !== sidebarIcon) {
            console.error("Sidebar icon has not been updated.");
        }
    },
},
// Update icon of active article from sidebar
{
    // Click on the icon in the sidebar
    trigger: '.o_article_active .o_article_emoji',
}, {
    // Choose an icon
    trigger: '.o-Emoji[data-codepoints="🥶"]',
}, {
    // Check that the icon has been updated in both trees in the sidebar
    trigger: 'section[data-section="favorites"] .o_article_active .o_article_emoji:contains("🥶")',
    extra_trigger: 'section[data-section="private"] .o_article_active .o_article_emoji:contains("🥶")',
    run: () => {},
}, {
    // Check that the icon in the body has been updated
    trigger: '.o_knowledge_body div[name="icon"]:contains("🥶")',
    run: () => {},
},
// Update icon of non active article
{
    // Click on the icon in the sidebar
    trigger: '.o_article:contains("Workspace Article") .o_article_emoji',
}, {
    // Choose an icon
    trigger: '.o-Emoji[data-codepoints="🥵"]',
}, {
    // Check that the icon has been updated in the sidebar
    trigger: '.o_article:contains("Workspace Article") .o_article_emoji:contains("🥵")',
    run: () => {},
}, {
    // Check that the icon in the body has not been updated
    trigger: '.o_knowledge_body div[name="icon"]:contains("🥶")',
    run: () => {},
},
// Update icon of locked article (fails)
{
    // Open another article
    trigger: '.o_article_name:contains("Workspace Child")',
}, {
    // Lock the article
    trigger: '#dropdown_tools_panel',
    extra_trigger: '.o_article_active:contains("Workspace Child")',
}, {
    trigger: '.o_knowledge_more_options_panel .btn-lock',
}, {
    // Click on the icon of the active article in the sidebar
    trigger: '.o_article_active .o_article_emoji:contains("📄")',
    extra_trigger: '.breadcrumb-item.active .fa-lock',
}, {
    // Check that emoji picker did not show up
    trigger: 'body:not(:has(.o-EmojiPicker))',
    run: () => {},
},
// Update icon of unlocked article
{
    // Unlock the article
    trigger: '#dropdown_tools_panel',
}, {
    trigger: '.o_knowledge_more_options_panel .btn-lock .fa-unlock',
}, {
    // Click on the icon of the active article in the sidebar
    trigger: '.o_article_active a.o_article_emoji',
    extra_trigger: '.breadcrumb-item.active:not(:has(.fa-lock))',
}, {
    // Choose an icon
    trigger: '.o-Emoji[data-codepoints="😬"]',
}, {
    // Check that the icon has been updated in the sidebar
    trigger: '.o_article:contains("Workspace Child") .o_article_emoji:contains("😬")',
    run: () => {},
},
// Convert article into item
{
    // Open the kebab menu
    trigger: '#dropdown_tools_panel',
}, {
    // Click on convert button
    trigger: '.dropdown-item .fa-tasks',
}, {
    // Check that article has been removed from the sidebar
    trigger: 'section[data-section="workspace"] .o_article:not(:has(.o_article))',
    extra_trigger: 'section[data-section="workspace"] .o_article:contains("Workspace Article"):not(.o_article_has_children)',
    run: () => {},
},
// Favorite an item
{
    // Click on the toggle favorite button
    trigger: '.o_knowledge_toggle_favorite',
}, {
    // Check that item has been added in the favorite section
    trigger: 'section[data-section="favorites"] .o_article:contains("Workspace Child")',
    run: () => {},
},
// Convert item into article
{
    // Open the kebab menu
    trigger: '#dropdown_tools_panel',
}, {
    // Click on convert button
    trigger: '.dropdown-item .fa-sitemap',
}, {
    // Check that article has been readded in the main tree
    trigger: 'section[data-section="workspace"] .o_article:contains("Workspace Child")',
    run: () => {},
},
// Convert a favorite article to an item
{
    // Open the kebab menu
    trigger: '#dropdown_tools_panel',
}, {
    // Click on the convert button
    trigger: '.dropdown-item .fa-tasks',
}, {
    // Check that article has been removed from the main tree but not from the favorite tree
    trigger: 'section[data-section="workspace"] .o_article:not(:has(.o_article))',
    extra_trigger: 'section[data-section="workspace"] .o_article:contains("Workspace Article"):not(.o_article_has_children)',
    run: () => {},
}, {
    // Check that article has not been removed from the favorite tree
    trigger: 'section[data-section="favorites"] .o_article:contains("Workspace Child")',
    run: () => {},
},
// Remove member of child of shared article
{
    // Open the shared child article
    trigger: '.o_article_name:contains("Shared Child")',
}, {
    // Open the share dropdown
    trigger: '.o_knowledge_header .btn:contains("Share")',
    extra_trigger: '.o_article_active:contains("Shared Child")',
}, {
    // Make remove member button visible
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => {
        document.querySelector('.o_knowledge_share_panel .o_delete.o_remove').style.display = 'block';
    },
}, {
    // Click on the delete member button
    trigger: '.o_knowledge_share_panel .o_delete.o_remove',
}, {
    // Confirm restriction
    trigger: '.modal-footer .btn-primary',
}, {
    // Check that the article did not move
    trigger: 'section[data-section="shared"] .o_article .o_article',
    extra_trigger: '.o_knowledge_share_panel_icon',
},
// Publish child of a shared article
{
    // Open the share dropdown
    trigger: '.o_knowledge_header .btn:contains("Share")',
}, {
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    extra_trigger: '.o_permission[aria-label="Internal Permission"]',
    run: () => changeInternalPermission('write'),
}, {
    // Check that the article did not move
    trigger: 'section[data-section="shared"] .o_article .o_article',
    run: () => {},
},
// Publish shared article
{
    // Open shared article
    trigger: '.o_article_name:contains("Shared Article")',
}, {
    // Open the share dropdown
    trigger: '.o_knowledge_header .btn:contains("Share")',
    extra_trigger: '.o_article_active:contains("Shared Article")',
}, {
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('write'),
}, {
    // Check that the article moved to the workspace
    trigger: 'section[data-section="workspace"] .o_article:contains("Shared Article")',
    run: () => {},
}, 
// Restrict workspace article with member
{
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('none'),
}, {
    // Check that article moved to shared
    trigger: 'section[data-section="shared"] .o_article:contains("Shared Article")',
    run: () => {},
},
// Remove member of shared article
{
    // Make remove member button visible
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => {
        document.querySelector('.o_knowledge_share_panel .o_delete.o_remove').style.display = 'block';
    },
}, {
    // Remove member
    trigger: '.o_knowledge_share_panel .o_delete.o_remove',
}, {
    // Check that article moved to private
    trigger: 'section[data-section="private"] .o_article:contains("Shared Article")',
}, {
    // Readd the member to replace the article in the shared section
    trigger: '.o_knowledge_header .btn:contains("Share")',
}, {
    trigger: '.o_knowledge_share_panel .btn:contains("Invite")',
}, {
    trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
    run: 'text henri@knowledge.com',
}, {
    trigger: '.o-autocomplete--dropdown-item:contains("henri@")',
    extra_trigger: '.o-autocomplete--dropdown-menu.show',
}, {
    trigger: 'button:contains("Invite")',
    extra_trigger: '.o_field_tags span.o_badge_text',
},
// Publish child of private article
{
    // Open private child
    trigger: '.o_article_name:contains("Private Child 2")',
}, {
    // Open the share dropown
    trigger: '.o_knowledge_header .btn:contains("Share")',
    extra_trigger: '.o_article_active:contains("Private Child 2")',
}, {
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('read'),
}, {
    // Check that article is still in private
    trigger: 'section[data-section="private"] .o_article .o_article:contains("Private Child 2")',
    run: () => {},
},
// Publish private article
{
    // Open private article
    trigger: '.o_article_name:contains("Private Article")',
}, {
    // Open the share dropdown
    trigger: '.o_knowledge_header .btn:contains("Share")',
    extra_trigger: '.o_article_active:contains("Private Article")',
}, {
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('read'),
}, {
    // Check that article moved to the workspace
    trigger: 'section[data-section="workspace"] .o_article:contains("Private Article")',
    run: () => {},
},
// Change permission of workspace article to write
{
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('write'),
}, {
    // Check that article did not move
    trigger: 'section[data-section="workspace"] .o_article:contains("Private Article")',
    run: () => {},
},
// Change permission of workspace article to read
{
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('read'),
}, {
    // Check that article did not move
    trigger: 'section[data-section="workspace"] .o_article:contains("Private Article")',
    run: () => {},
}, 
// Restrict workspace article
{
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('none'),
}, {
    // Check that the article moved to private
    trigger: 'section[data-section="private"] .o_article:contains("Private Article")',
    run: () => {},
},
// Drag and drop child above other child
{
    trigger: 'section[data-section="private"] .o_article .o_article:first:contains("Private Child 1")',
    run: () => {
        dragAndDropArticle(
            $('.o_section[data-section="private"] .o_article_name:contains("Private Child 3")'),
            $('.o_section[data-section="private"] .o_article_name:contains("Private Child 1")'),
        );
    },
}, {
    // Check that children have been reordered in both trees
    trigger: 'section[data-section="favorites"] .o_article .o_article:first:contains("Private Child 3")',
    extra_trigger: 'section[data-section="private"] .o_article .o_article:first:contains("Private Child 3")',
},
// Drag and drop child above root
{
    // Open child article
    trigger: '.o_article_name:contains("Private Child 2")',
}, {
    // Check that article shows "Add Properties" button
    trigger: '.o_knowledge_add_buttons',
    extra_trigger: '.o_article_active:contains("Private Child 2")',
    run: () => {
        if (!document.querySelector('.o_knowledge_add_buttons .o_knowledge_add_properties')) {
            console.error('Child articles should have properties.');
        }
    },
}, {
    trigger: 'section[data-section="private"] .o_article:first:contains("Private Article")',
    run: () => {
        dragAndDropArticle(
            $('.o_section[data-section="private"] .o_article_name:contains("Private Child 2")'),
            $('.o_section[data-section="private"] .o_article_name:contains("Private Article")'),
        );
    },
}, {
    // Check that child became the first private root article
    trigger: '.o_section[data-section="private"] .o_article:not(:has(.o_article:contains("Private Child 2")))',
    extra_trigger: '.o_section[data-section="private"] ul >:first:contains("Private Child 2")',
    run: () => {},
}, {
    // Check that article was removed from children in favorites
    trigger: '.o_section[data-section="favorites"]:not(:has(.o_article:contains("Private Child 2")))',
    run: () => {
        makeVisible('.o_knowledge_add_buttons');
    }
}, {
    // Check that article does not show "Add Properties" button anymore
    trigger: '.o_knowledge_add_buttons:not(:has(button.o_knowledge_add_properties))',
    run: () => {},
},
// Drag and drop root above root
{
    trigger: '.o_section[data-section="private"] .o_article:contains("Private Child 2") + .o_article:contains("Private Article")',
    run: () => {
        dragAndDropArticle(
            $('.o_section[data-section="private"] .o_article_name:contains("Private Article")'),
            $('.o_section[data-section="private"] .o_article_name:contains("Private Child 2")'),
        );
    },
}, {
    // Check that the articles have been reordered
    trigger: '.o_section[data-section="private"] .o_article:contains("Private Article") + .o_article:contains("Private Child 2")',
    run: () => {
        makeVisible('section[data-section="private"] .o_section_create');
    },
},
// Drag and drop root above child
{
    // Create a new article
    trigger: 'section[data-section="private"] .o_section_create',
}, {
    // Rename the article
    trigger: '.o_breadcrumb_article_name > input',
    extra_trigger: '.o_article_active:contains("Untitled")',
    run: 'text Private Child 4',
}, {
    trigger: '.o_article_active:contains("Private Child 4")',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="private"] .o_article_name:contains("Private Child 4")'),
            $('section[data-section="private"] .o_article_name:contains("Private Child 1")'),
        );
    },
}, {
    // Check that the children are correclty ordered
    trigger: 'section[data-section="private"] .o_article:contains("Private Child 3") + .o_article:contains("Private Child 4")',
    extra_trigger: 'section[data-section="private"] .o_article:contains("Private Child 4") + .o_article:contains("Private Child 1")',
    run: () => {},
}, {
    // Check that the children are also ordered in the favorite tree
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Child 3") + .o_article:contains("Private Child 4")',
    extra_trigger: 'section[data-section="favorites"] .o_article:contains("Private Child 4") + .o_article:contains("Private Child 1")',
    run: () => {},
},
// Drag and drop workspace to private
{
    trigger: 'section[data-section="workspace"] .o_article:contains("Workspace Article")',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="workspace"] .o_article:contains("Workspace Article")'),
            $('section[data-section="private"]'),
        );
    },
}, {
    // Moving from section should ask for confirmation
    trigger: '.modal-footer .btn-primary',
}, {
    // Check that article moved to the private section
    trigger: 'section[data-section="private"] .o_article:contains("Workspace Article")',
    extra_trigger: 'section[data-section="workspace"]:not(:has(.o_article:contains("Workspace Article")))',
    run: () => {},
}, {
    // Show that empty section message is shown
    trigger: 'section[data-section="workspace"] .o_knowledge_empty_info',
    run: () => {},
},
// Cancel drag and drop
{
    trigger: '.o_knowledge_tree',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="private"] .o_article_name:contains("Workspace Article")'),
            $('section[data-section="workspace"] .o_section_header'),
        );
    },
}, {
    // Cancel the move
    trigger: '.modal-footer .btn-secondary',
}, {
    // Check that the article did not move
    trigger: 'section[data-section="private"] .o_article:contains("Workspace Article")',
    extra_trigger: 'section[data-section="workspace"]:not(:has(.o_article:contains("Workspace Article")))',
    run: () => {},
},
// Drag and drop private to workspace
{
    trigger: '.o_knowledge_tree',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="private"] .o_article_name:contains("Workspace Article")'),
            $('section[data-section="workspace"]'),
        );
    },
}, {
    // Moving from section should ask for confirmation
    trigger: '.modal-footer .btn-primary',
}, {
    // Check that article moved to the workspace section
    trigger: 'section[data-section="workspace"] .o_article:contains("Workspace Article")',
    extra_trigger: 'section[data-section="private"]:not(:has(.o_article:contains("Workspace Article")))',
    run: () => {},
}, {
    // Check that the empty section message disappeared
    trigger: 'section[data-section="workspace"]:not(:has(.o_knowledge_empty_info))',
    run: () => {},
},
// Drag and drop article to shared (fails)
{
    trigger: '.o_article:contains("Private Article")',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="private"] .o_article:contains("Private Article")'),
            $('section[data-section="shared"]'),
        );
    },
}, {
    // Close the move cancelled modal
    trigger: '.modal-footer .btn-primary',
    extra_trigger: '.modal-title:contains("Move cancelled")',
},
// Resequence shared articles
{
    trigger: 'section[data-section="private"]',
    run: () => {
        makeVisible('section[data-section="private"] .o_section_create');
    },
}, {
    // Create a new shared article
    trigger: 'section[data-section="private"] .o_section_create',
}, {
    // Rename the article
    trigger: '.o_breadcrumb_article_name > input',
    extra_trigger: '.o_article_active:contains("Untitled")',
    run: 'text Shared 2',
}, {
    // Share the article
    trigger: '.o_knowledge_header .btn:contains("Share")',
}, {
    trigger: '.o_knowledge_share_panel .btn:contains("Invite")',
}, {
    trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
    run: 'text henri@knowledge.com',
}, {
    trigger: '.o-autocomplete--dropdown-item:contains("henri@")',
    extra_trigger: '.o-autocomplete--dropdown-menu.show',
}, {
    trigger: 'button:contains("Invite")',
    extra_trigger: '.o_field_tags span.o_badge_text',
}, {
    trigger: 'section[data-section="shared"] .o_article:contains("Shared Article") + .o_article:contains("Shared 2")',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="shared"] .o_article_name:contains("Shared 2")'),
            $('section[data-section="shared"] .o_article_name:contains("Shared Article")'),
        );
    },
}, {
    // Check that the articles have been resequenced
    trigger: 'section[data-section="shared"] .o_article:contains("Shared 2") + .o_article:contains("Shared Article")',
    run: () => {
        makeVisible('section[data-section="private"] .o_section_create');
    },
},
// Drag and drop article above shared child
{
    // Create a new article
    trigger: 'section[data-section="private"] .o_section_create',
}, {
    // Rename the article
    trigger: '.o_breadcrumb_article_name > input',
    extra_trigger: '.o_article_active:contains("Untitled")',
    run: 'text Moved to Share',
}, {
    trigger: '.o_article_active:contains("Moved to Share")',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="private"] .o_article_name:contains("Moved to Share")'),
            $('section[data-section="shared"] .o_article_name:contains("Shared Child")'),
        );
    },
}, {
    // Moving under a shared article should ask for confirmation
    trigger: '.modal-footer .btn-primary',
}, {
    // Check that the article has been moved
    trigger: 'section[data-section="shared"] .o_article .o_article:contains("Moved to Share")',
    extra_trigger: 'section[data-section="private"]:not(:has(.o_article:contains("Moved to Share")))',
    run: () => {},
},
// Drag and drop shared child to shared
{
    trigger: '.o_knowledge_tree',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="shared"] .o_article_name:contains("Moved to Share")'),
            $('section[data-section="shared"] .o_article_name:contains("Shared Article")'),
        );
    },
}, {
    // Close the move cancelled modal
    trigger: '.modal-footer .btn-primary',
    extra_trigger: '.modal-title:contains("Move cancelled")',
},
// Drag and drop article to trash
{
    trigger: '.o_knowledge_tree',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="private"] .o_article_name:contains("Private Child 2")'),
            $('.o_section.o_knowledge_sidebar_trash'),
        );
    },
}, {
    // Check that article has been removed from the sidebar
    trigger: '.o_knowledge_tree:not(:has(.o_article:contains("Private Child 2")))',
    run: () => {},
},
// Drag and drop parent of active article to trash
{
    trigger: '.o_article_active:contains("Moved to Share")',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="shared"] .o_article_name:contains("Shared Article")'),
            $('.o_section.o_knowledge_sidebar_trash'),
        );
    },
}, {
    // Check that article has been removed from the sidebar
    trigger: '.o_knowledge_tree:not(:has(.o_article:contains("Shared Article")))',
    run: () => {},
}, {
    // Check that user has been redirected to first accessible article
    trigger: '.o_knowledge_tree .o_article:first:has(.o_article_active)',
    run: () => {},
},
// Resequence favorites
{
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article") + .o_article:contains("Workspace Child")',
    run: () => {
        dragAndDropArticle(
            $('section[data-section="favorites"] .o_article_name:contains("Workspace Child")'),
            $('section[data-section="favorites"] .o_article_name:contains("Private Article")'),
        );
    },
}, {
    // Check that favorites have been resequenced
    trigger: 'section[data-section="favorites"] .o_article:contains("Workspace Child") + .o_article:contains("Private Article")',
    run: () => {},
}]});
