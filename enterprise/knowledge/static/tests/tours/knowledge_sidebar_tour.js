/** @odoo-module */

import {
    changeInternalPermission,
    dragAndDropArticle,
} from "@knowledge/../tests/tours/knowledge_tour_utils";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

/**
 * Sidebar tour.
 * Tests sidebar features and responsiveness.
 * Todo: add responsiveness checks from usage of moveArticleDialog
 * when select2 will be replaced (can currently not select options)
 */

registry.category("web_tour.tours").add('knowledge_sidebar_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    // Open the Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
    run: "click",
},
// Create a workspace article
{
    // Force the create button to be visible (it's only visible on hover)
    trigger: 'section[data-section="workspace"]',
    run: "hover && click section[data-section=workspace] .o_section_create",
}, {
    // Check that the article is created inside the Workspace
    trigger: 'section[data-section="workspace"] .o_article .o_article_name:contains("Untitled")',
}, {
    // Rename the article
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Workspace Article && click body",
}, {
    // Check that the name has been updated in the sidebar
    trigger: '.o_article_active:contains("Workspace Article")',
}, {
    // Add content to the article
    trigger: '.note-editable.odoo-editor-editable',
    run: "editor Content of Workspace Article",
},
// Create a private article
{
    // Force the create button to be visible (it's only visible on hover)
    trigger: 'section[data-section="private"]',
    run: "hover && click section[data-section=private] .o_section_create",
}, {
    // Check that the article is created inside the private section
    trigger: 'section[data-section="private"] .o_article .o_article_name:contains("Untitled")',
}, {
    // Rename the article
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Private Article && click body",
        },
        // Create a shared article
        {
            trigger: '.o_article_active:contains("Private Article")',
        },
        {
            content: "Check that the shared section does not exists",
            trigger: '.o_knowledge_tree:not(:has(section[data-section="shared"]))',
        },
        {
            content: "First create a private one",
            trigger: "section[data-section=private]",
            run: "hover && click section[data-section=private] .o_section_create",
        },
        {
            trigger: '.o_article_active:contains("Untitled")',
        },
        {
    // Rename the article
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Shared Article && click body",
}, {
    // Open the share dropdown
    trigger: '.o_knowledge_header .btn-share',
    run: "click",
}, {
    // Click on 'Invite'
    trigger: '.o_knowledge_share_panel .btn:contains("Invite")',
    run: "click",
}, {
    // Type the invited person's name
    trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
    run: "edit henri@knowledge.com",
}, {
    // Open the simplified create form view
    trigger: '.o-autocomplete--dropdown-menu .o_m2o_dropdown_option_create_edit a',
    run: "click",
        },
        {
            // Give an email address to the partner
            trigger: ".modal:not(.o_inactive_modal) .o_field_widget[name=email] input",
            run: "edit henri@knowledge.com",
        },
        {
            // Save the new partner
            trigger: ".modal:not(.o_inactive_modal) .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_field_tags span.o_badge_text",
        },
        {
            // Submit the invite wizard
            trigger: ".modal:not(.o_inactive_modal) button:contains(Invite)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal:contains(invite))",
        },
        {
            content: `Check that the article has been added to a new "Shared" section`,
            trigger: "section[data-section=shared]:contains(Shared Article)",
        },
        // Create a child of a workspace article
        {
            content: "Hover on Workspace Article to make create article visible",
            trigger: ".o_article:contains(Workspace Article)",
            run: "hover && click .o_article:contains(Workspace Article) a.o_article_create",
        },
        {
            content: "Check that the child has been added",
            trigger: '.o_article:contains("Workspace Article") .o_article:contains("Untitled")',
        },
        {
            content: "Rename the article",
            trigger: ".o_hierarchy_article_name > input",
            run: "edit Workspace Child && click body",
        },
        // Create a child of a private article
        {
            content: "Hover on Private Article to make create article visible",
            trigger: ".o_article:contains(Private Article)",
            run: "hover && click .o_article:contains(Private Article) a.o_article_create",
        },
        {
            content: "Check that the child has been added",
            trigger: ".o_article:contains(Private Article) .o_article:contains(Untitled)",
        },
        {
    // Rename the article
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Private Child 1 && click body",
},
// Create a child of a shared article
        {
            content: "Hover on Shared Article to make create article visible",
            trigger: ".o_article:contains(Shared Article)",
            run: "hover && click .o_article:contains(Shared Article) a.o_article_create",
        },
        {
            content: "Check that the child has been added",
            trigger: ".o_article:contains(Shared Article) .o_article:contains(Untitled)",
        },
        {
    // Rename the article
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Shared Child && click body",
},
// Open an article by clicking on it
{
    // Click in the sidebar
    trigger: '.o_article_name:contains("Workspace Article")',
    run: "click",
        },
        {
            trigger: '.o_article_active:contains("Workspace Article")',
        },
        {
    // Check that article is correctly opened
    trigger: '.note-editable.odoo-editor-editable:contains("Content of Workspace Article")',
},
// Open an article using the searchBox
{
    // Open the CP
    trigger: '#knowledge_search_bar',
    run: "click",
}, {
    trigger: '.o_command_palette_search input',
    run: 'edit Private Article',
}, {
    // Click on an article
    trigger: '.o_command_name:not(.small):contains("Private Article")',
    run: "click",
}, {
    // Check article was opened
    trigger: '.o_article_active .o_article_name:contains("Private Article")',
},
// Open the trash
{
    trigger: '.o_knowledge_sidebar_trash > div[role="button"]',
    run: "click",
}, {
    // Check that trash has been opened
    trigger: '.o_last_breadcrumb_item.active:contains("Trash")',
}, {
    // Come back to the form view
    trigger: '.breadcrumb-item.o_back_button',
    run: "click",
},
// Add/remove an article to/from the favorites
{
    // Make sure the favorite section does not exists
    trigger: '.o_knowledge_tree:not(:has(section[data-section="favorites"]))',
}, {
    // Click on the toggleFavorite button
    trigger: 'a.o_knowledge_toggle_favorite',
    run: "click",
}, {
    // Check that the article has been added to the added favorite section
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article")',
}, {
    // Click on the toggleFavorite button again
    trigger: 'a.o_knowledge_toggle_favorite',
    run: "click",
        },
        {
            trigger: 'a.o_knowledge_toggle_favorite .fa-star-o',
        },
        {
    // Check that the favorite section has been removed
    trigger: '.o_knowledge_tree:not(:has(section[data-section="favorites"]))',
    run: "click",
},
// Unfold/Fold favorite article
{
    // Add article to favorite
    trigger: 'a.o_knowledge_toggle_favorite',
    run: "click",
        },
        {
            trigger: 'section[data-section="favorites"] .o_article:not(:has(.o_article))',
        },
        {
    // Check that favorite is initially folded, and unfold it
    trigger: 'section[data-section="favorites"] .o_article_caret .fa-caret-right',
    run: "click",
        },
        {
            trigger: 'section[data-section="favorites"] .o_article_caret .fa-caret-down',
        },
        {
    // Check that caret changed and that child is displayed
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article") .o_article_name:contains("Private Child 1")',
}, {
    // Click on the caret again to refold the article
    trigger: 'section[data-section="favorites"] .o_article_caret',
    run: "click",
        },
        {
            trigger: 'section[data-section="favorites"] .o_article_caret .fa-caret-right',
        },
        {
            content: "Check that caret changed and that child is hidden again",
            trigger: 'section[data-section="favorites"] .o_article:not(:has(.o_article))',
        },
        {
            content: "Check that article in main tree is still unfolded",
            trigger: 'section[data-section="private"] .o_article:contains("Private Child 1")',
        },
        {
            trigger: 'section[data-section="favorites"] .o_article_caret .fa-caret-right',
        },
        {
            content: "Hover on Favorites Private Article to make create article visible",
            trigger: "section[data-section=favorites] .o_article:contains(Private Article)",
            run: "hover && click section[data-section=favorites] .o_article:contains(Private Article) a.o_article_create",
        },
        {
            content: "Check that article has been unfolded",
            trigger:
                'section[data-section="favorites"] .o_article:contains("Private Article") .fa-caret-down',
        },
        {
    // Check that previously existing child is displayed
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article") .o_article_name:contains("Private Child 1")',
}, {
    // Check that the child has been added in the favorite tree
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article") .o_article_name:contains("Untitled")',
}, {
    // Check that the child has been added in the private section
    trigger: 'section[data-section="private"] .o_article:contains("Private Article") .o_article_name:contains("Untitled")',
}, {
    // Rename the article
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Private Child 2 && click body",
}, {
    // Check that the article has been renamed in the favorite tree
    trigger: 'section[data-section="favorites"] .o_article_name:contains("Private Child 2")',
}, {
    // Check that the article has been renamed in the private section
    trigger: 'section[data-section="private"] .o_article_name:contains("Private Child 2")',
    // Fold/unfold an article
        },
        {
            trigger: 'section[data-section="private"] .o_article_caret .fa-caret-down',
        },
        {
            content: "Click on the caret (should be caret down)",
            trigger: 'section[data-section="private"] .o_article_caret',
            run: "click",
        },
        {
            trigger: 'section[data-section="private"] .o_article_caret .fa-caret-right',
        },
        {
            content:
                "Check that caret changed, and that children are hidden, and that favorite has not been folded",
            trigger: 'section[data-section="private"] .o_article:not(:has(.o_article))',
        },
        {
            trigger:
                'section[data-section="favorites"] .o_article_handle:contains("Private Article") .fa-caret-down',
        },
        {
    // Check that favorite has not been folded
    trigger: 'section[data-section="favorites"] .o_article .o_article',
    run: "click",
}, {
    // Fold favorite article (to later check that unfolding article won't unfold favorite)
    trigger: 'section[data-section="favorites"] .o_article_caret',
    run: "click",
}, {
    // Click on the caret again
    trigger: 'section[data-section="private"] .o_article_caret',
    run: "click",
        },
        {
            trigger: 'section[data-section="private"] .o_article_caret .fa-caret-down',
        },
        {
    // Check that articles are shown again
    trigger: 'section[data-section="private"] .o_article .o_article',
        },
        {
            trigger: 'section[data-section="favorites"] .o_article_handle:contains("Private Article") .fa-caret-right',
        },
        {
    // Check that favorite has not been unfolded
    trigger: 'section[data-section="favorites"] .o_article:not(:has(.o_article))',
},
// Create a child of a folded article
{
    // Fold article again
    trigger: 'section[data-section="private"] .o_article_caret',
    run: "click",
}, 
        {
            trigger: "section[data-section=private] .o_article_caret .fa-caret-right",
        },
        {
            content: "Hover on Private Section => Private Article to make create article visible",
            trigger: "section[data-section=private] .o_article:contains(Private Article)",
            run: "hover && click section[data-section=private] .o_article:contains(Private Article) a.o_article_create",
        },
        {
            trigger: 'section[data-section="private"] .o_article_caret .fa-caret-down',
        },
        {
            content:
                "Check that article has been unfolded and that previously existing children are shown",
            trigger:
                'section[data-section="private"] .o_article .o_article:contains("Private Child 1")',
        },
        {
            trigger: 'section[data-section="favorites"] .o_article .o_article:contains("Untitled")',
        },
        {
    // Check that article has been added in both trees
    trigger: 'section[data-section="private"] .o_article .o_article:contains("Untitled")',
}, {
    // Rename the article
    trigger: '.o_hierarchy_article_name > input',
    run: 'edit Private Child 3 && click body',
},
// Add a random icon
{
    trigger: '#dropdown_tools_panel',
    run: "click",
}, {
    // Click on the "add Icon" button
    trigger: '.o_knowledge_add_icon',
    run: "click",
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
    run: "click",
}, {
    // Choose an icon
    trigger: '.o-Emoji[data-codepoints="🥶"]',
    run: "click",
        },
        {
            trigger: 'section[data-section="private"] .o_article_active .o_article_emoji:contains("🥶")',
        },
        {
    // Check that the icon has been updated in both trees in the sidebar
    trigger: 'section[data-section="favorites"] .o_article_active .o_article_emoji:contains("🥶")',
}, {
    // Check that the icon in the body has been updated
    trigger: '.o_knowledge_body div[name="icon"]:contains("🥶")',
},
// Update icon of non active article
{
    // Click on the icon in the sidebar
    trigger: '.o_article:contains("Workspace Article") .o_article_emoji',
    run: "click",
}, {
    // Choose an icon
    trigger: '.o-Emoji[data-codepoints="🥵"]',
    run: "click",
}, {
    // Check that the icon has been updated in the sidebar
    trigger: '.o_article:contains("Workspace Article") .o_article_emoji:contains("🥵")',
}, {
    // Check that the icon in the body has not been updated
    trigger: '.o_knowledge_body div[name="icon"]:contains("🥶")',
},
// Update icon of locked article (fails)
{
    // Open another article
    trigger: '.o_article_name:contains("Workspace Child")',
    run: "click",
        },
        {
            trigger: '.o_article_active:contains("Workspace Child")',
        },
        {
    // Lock the article
    trigger: '#dropdown_tools_panel',
    run: "click",
}, {
    trigger: '.o_knowledge_more_options_panel .btn-lock',
    run: "click",
        },
        {
            trigger: '.o_knowledge_header > div > i.fa-lock',
        },
        {
    // Click on the icon of the active article in the sidebar
    trigger: '.o_article_active .o_article_emoji:contains("📄")',
    run: "click",
}, {
    // Check that emoji picker did not show up
    trigger: 'body:not(:has(.o-EmojiPicker))',
},
// Update icon of unlocked article
{
    // Unlock the article
    trigger: '#dropdown_tools_panel',
    run: "click",
}, {
    trigger: '.o_knowledge_more_options_panel .btn-lock .fa-unlock',
    run: "click",
        },
        {
            trigger: '.o_knowledge_header > div:not(:has(> i.fa-lock))',
        },
        {
    // Click on the icon of the active article in the sidebar
    trigger: '.o_article_active a.o_article_emoji',
    run: "click",
}, {
    // Choose an icon
    trigger: '.o-Emoji[data-codepoints="😬"]',
    run: "click",
}, {
    // Check that the icon has been updated in the sidebar
    trigger: '.o_article:contains("Workspace Child") .o_article_emoji:contains("😬")',
},
// Convert article into item
{
    // Open the kebab menu
    trigger: '#dropdown_tools_panel',
    run: "click",
}, {
    // Click on convert button
    trigger: '.dropdown-item .fa-tasks',
    run: "click",
        },
        {
            trigger: 'section[data-section="workspace"] .o_article:contains("Workspace Article"):not(.o_article_has_children)',
        },
        {
    // Check that article has been removed from the sidebar
    trigger: 'section[data-section="workspace"] .o_article:not(:has(.o_article))',
},
// Favorite an item
{
    // Click on the toggle favorite button
    trigger: '.o_knowledge_toggle_favorite',
    run: "click",
}, {
    // Check that item has been added in the favorite section
    trigger: 'section[data-section="favorites"] .o_article:contains("Workspace Child")',
},
// Convert item into article
{
    // Open the kebab menu
    trigger: '#dropdown_tools_panel',
    run: "click",
}, {
    // Click on convert button
    trigger: '.dropdown-item .fa-sitemap',
    run: "click",
}, {
    // Check that article has been readded in the main tree
    trigger: 'section[data-section="workspace"] .o_article:contains("Workspace Child")',
},
// Convert a favorite article to an item
{
    // Open the kebab menu
    trigger: '#dropdown_tools_panel',
    run: "click",
}, {
    // Click on the convert button
    trigger: '.dropdown-item .fa-tasks',
    run: "click",
        },
        {
            trigger: 'section[data-section="workspace"] .o_article:contains("Workspace Article"):not(.o_article_has_children)',
        },
        {
    // Check that article has been removed from the main tree but not from the favorite tree
    trigger: 'section[data-section="workspace"] .o_article:not(:has(.o_article))',
}, {
    // Check that article has not been removed from the favorite tree
    trigger: 'section[data-section="favorites"] .o_article:contains("Workspace Child")',
},
        // Remove member of child of shared article
        {
            content: "Open the shared child article",
            trigger: ".o_article_name:contains(Shared Child)",
            run: "click",
        },
        {
            content: "Open the share dropdown",
            trigger: ".o_knowledge_header .btn-share",
            run: "click",
        },
        {
            content: "Make remove member button visible and click on the delete member button",
            trigger: ".o_knowledge_share_panel:not(:has(.fa-spin))",
            run: "hover && click .o_knowledge_share_panel .o_delete.o_remove",
        },
        {
            content: "Confirm restriction",
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: ".o_knowledge_share_panel_icon",
        },
        {
    // Check that the article did not move
    trigger: 'section[data-section="shared"] .o_article .o_article',
    run: "click",
},
// Publish child of a shared article
{
    // Open the share dropdown
    trigger: '.o_knowledge_header .btn-share',
    run: "click",
        },
        {
            trigger: '.o_permission[aria-label="Internal Permission"]',
        },
        {
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('write'),
}, {
    // Check that the article did not move
    trigger: 'section[data-section="shared"] .o_article .o_article',
},
// Publish shared article
{
    // Open shared article
    trigger: '.o_article_name:contains("Shared Article")',
    run: "click",
        },
        {
            trigger: '.o_article_active:contains("Shared Article")',
        },
        {
    // Open the share dropdown
    trigger: '.o_knowledge_header .btn-share',
    run: "click",
}, {
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('write'),
}, {
    // Check that the article moved to the workspace
    trigger: 'section[data-section="workspace"] .o_article:contains("Shared Article")',
},
// Restrict workspace article with member
{
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('none'),
}, {
    // Check that article moved to shared
    trigger: 'section[data-section="shared"] .o_article:contains("Shared Article")',
},
// Remove member of shared article
        {
            content: "Make remove member button visible and click on the delete member button",
            trigger: ".o_knowledge_share_panel:not(:has(.fa-spin))",
            run: "hover && click .o_knowledge_share_panel .o_delete.o_remove",
        },
        {
    // Check that article moved to private
    trigger: 'section[data-section="private"] .o_article:contains("Shared Article")',
    run: "click",
}, {
    // Readd the member to replace the article in the shared section
    trigger: '.o_knowledge_header .btn-share',
    run: "click",
}, {
    trigger: '.o_knowledge_share_panel .btn:contains("Invite")',
    run: "click",
}, {
    trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
    run: "edit henri@knowledge.com",
        },
        {
            trigger: '.o-autocomplete--dropdown-menu.show',
        },
        {
    trigger: '.o-autocomplete--dropdown-item:contains("henri@")',
    run: "click",
        },
        {
            trigger: '.o_field_tags span.o_badge_text',
        },
        {
            trigger: ".modal button:contains(Invite)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        // Publish child of private article
        {
            content: "Open private child",
            trigger: ".o_article_name:contains(Private Child 2)",
            run: "click",
        },
        {
            trigger: '.o_article_active:contains("Private Child 2")',
        },
        {
    // Open the share dropown
    trigger: '.o_knowledge_header .btn-share',
    run: "click",
}, {
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('read'),
}, {
    // Check that article is still in private
    trigger: 'section[data-section="private"] .o_article .o_article:contains("Private Child 2")',
},
// Publish private article
{
    // Open private article
    trigger: '.o_article_name:contains("Private Article")',
    run: "click",
        },
        {
            trigger: '.o_article_active:contains("Private Article")',
        },
        {
    // Open the share dropdown
    trigger: '.o_knowledge_header .btn-share',
    run: "click",
}, {
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('read'),
}, {
    // Check that article moved to the workspace
    trigger: 'section[data-section="workspace"] .o_article:contains("Private Article")',
},
// Change permission of workspace article to write
{
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('write'),
}, {
    // Check that article did not move
    trigger: 'section[data-section="workspace"] .o_article:contains("Private Article")',
},
// Change permission of workspace article to read
{
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('read'),
}, {
    // Check that article did not move
    trigger: 'section[data-section="workspace"] .o_article:contains("Private Article")',
},
// Restrict workspace article
{
    // Change permission
    trigger: '.o_knowledge_share_panel:not(:has(.fa-spin))',
    run: () => changeInternalPermission('none'),
}, {
    // Check that the article moved to private
    trigger: 'section[data-section="private"] .o_article:contains("Private Article")',
},
// Drag and drop child above other child
{
    trigger: 'section[data-section="private"] .o_article .o_article:first:contains("Private Child 1")',
    run: () => {
        dragAndDropArticle(
            '.o_section[data-section="private"] .o_article_name:contains("Private Child 3")',
            '.o_section[data-section="private"] .o_article_name:contains("Private Child 1")',
        );
    },
        },
        {
            trigger: 'section[data-section="private"] .o_article .o_article:first:contains("Private Child 3")',
        },
        {
    // Check that children have been reordered in both trees
    trigger: 'section[data-section="favorites"] .o_article .o_article:first:contains("Private Child 3")',
    run: "click",
},
// Drag and drop child above root
{
    // Open child article
    trigger: '.o_article_name:contains("Private Child 2")',
    run: "click",
        },
        {
            trigger: '.o_article_active:contains("Private Child 2")',
        },
        {
    // Check that article shows "Add Properties" button
    trigger: '#dropdown_tools_panel',
    run: "click",
}, {
    trigger: '.o_knowledge_add_properties',
}, {
    trigger: 'section[data-section="private"] .o_article:first:contains("Private Article")',
    run: () => {
        dragAndDropArticle(
            '.o_section[data-section="private"] .o_article_name:contains("Private Child 2")',
            '.o_section[data-section="private"] .o_article_name:contains("Private Article")',
        );
    },
        },
        {
            trigger: '.o_section[data-section="private"] ul li:first:contains("Private Child 2")',
        },
        {
    // Check that child became the first private root article
    trigger: '.o_section[data-section="private"] .o_article:not(:has(.o_article:contains("Private Child 2")))',
}, {
    // Check that article was removed from children in favorites
    trigger: '.o_section[data-section="favorites"]:not(:has(.o_article:contains("Private Child 2")))',
}, {
    // Check that article does not show "Add Properties" button anymore
    trigger: '.o_knowledge_more_options_panel:not(:has(button.o_knowledge_add_properties))',
},
// Drag and drop root above root
{
    trigger: '.o_section[data-section="private"] .o_article:contains("Private Child 2") + .o_article:contains("Private Article")',
    run: () => {
        dragAndDropArticle(
            '.o_section[data-section="private"] .o_article_name:contains("Private Article")',
            '.o_section[data-section="private"] .o_article_name:contains("Private Child 2")',
        );
    },
}, {
    // Check that the articles have been reordered
    trigger: '.o_section[data-section="private"] .o_article:contains("Private Article") + .o_article:contains("Private Child 2")',
},
// Drag and drop root above child
        {
            content: "Create a new article",
            trigger: "section[data-section=private]",
            run: "hover && click section[data-section=private] .o_section_create",
        },
        {
            trigger: '.o_article_active:contains("Untitled")',
        },
        {
    // Rename the article
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Private Child 4 && click body",
}, {
    trigger: '.o_article_active:contains("Private Child 4")',
    run: () => {
        dragAndDropArticle(
            'section[data-section="private"] .o_article_name:contains("Private Child 4")',
            'section[data-section="private"] .o_article_name:contains("Private Child 1")',
        );
    },
        },
        {
            trigger: 'section[data-section="private"] .o_article:contains("Private Child 4") + .o_article:contains("Private Child 1")',
        },
        {
    // Check that the children are correctly ordered
    trigger: 'section[data-section="private"] .o_article:contains("Private Child 3") + .o_article:contains("Private Child 4")',
        },
        {
            trigger: 'section[data-section="favorites"] .o_article:contains("Private Child 4") + .o_article:contains("Private Child 1")',
        },
        {
    // Check that the children are also ordered in the favorite tree
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Child 3") + .o_article:contains("Private Child 4")',
},
// Drag and drop workspace to private
{
    trigger: 'section[data-section="workspace"] .o_article:contains("Workspace Article")',
    run: () => {
        dragAndDropArticle(
            'section[data-section="workspace"] .o_article:contains("Workspace Article")',
            'section[data-section="private"]',
        );
    },
}, {
    // Moving from section should ask for confirmation
    trigger: '.modal-footer .btn-primary',
    run: "click",
        },
        {
            trigger: 'section[data-section="workspace"]:not(:has(.o_article:contains("Workspace Article")))',
        },
        {
    // Check that article moved to the private section
    trigger: 'section[data-section="private"] .o_article:contains("Workspace Article")',
}, {
    // Show that empty section message is shown
    trigger: 'section[data-section="workspace"] .o_knowledge_empty_info',
},
// Cancel drag and drop
{
    trigger: '.o_knowledge_tree',
    run: () => {
        dragAndDropArticle(
            'section[data-section="private"] .o_article_name:contains("Workspace Article")',
            'section[data-section="workspace"] .o_section_header',
        );
    },
        },
        {
            content: "Cancel the move",
            trigger: ".modal-footer .btn-secondary:enabled",
            run: "click",
        },
        {
            trigger: 'section[data-section="workspace"]:not(:has(.o_article:contains("Workspace Article")))',
        },
        {
    // Check that the article did not move
    trigger: 'section[data-section="private"] .o_article:contains("Workspace Article")',
},
// Drag and drop private to workspace
{
    trigger: '.o_knowledge_tree',
    run: () => {
        dragAndDropArticle(
            'section[data-section="private"] .o_article_name:contains("Workspace Article")',
            'section[data-section="workspace"]',
        );
    },
}, {
    // Moving from section should ask for confirmation
    trigger: '.modal-footer .btn-primary',
    run: "click",
        },
        {
            trigger: 'section[data-section="private"]:not(:has(.o_article:contains("Workspace Article")))',
        },
        {
    // Check that article moved to the workspace section
    trigger: 'section[data-section="workspace"] .o_article:contains("Workspace Article")',
}, {
    // Check that the empty section message disappeared
    trigger: 'section[data-section="workspace"]:not(:has(.o_knowledge_empty_info))',
},
// Drag and drop article to shared (fails)
{
    trigger: '.o_article:contains("Private Article")',
    run: () => {
        dragAndDropArticle(
            'section[data-section="private"] .o_article:contains("Private Article")',
            'section[data-section="shared"]',
        );
    },
        },
        {
            trigger: '.modal-title:contains("Move cancelled")',
        },
        {
    // Close the move cancelled modal
    trigger: '.modal-footer .btn-primary',
    run: "click",
},
// Resequence shared articles
{
            content: "Create a new shared article",
            trigger: "section[data-section=private]",
            run: "hover && click  section[data-section=private] .o_section_create",
        },
        {
            trigger: '.o_article_active:contains("Untitled")',
        },
        {
    // Rename the article
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Shared 2 && click body",
}, {
    // Share the article
    trigger: '.o_knowledge_header .btn-share',
    run: "click",
}, {
    trigger: '.o_knowledge_share_panel .btn:contains("Invite")',
    run: "click",
}, {
    trigger: '.o_field_many2many_tags_email[name=partner_ids] input',
    run: 'edit henri@knowledge.com',
        },
        {
            trigger: '.o-autocomplete--dropdown-menu.show',
        },
        {
    trigger: '.o-autocomplete--dropdown-item:contains("henri@")',
    run: "click",
        },
        {
            trigger: '.o_field_tags span.o_badge_text',
        },
        {
            trigger: ".modal button:contains(Invite)",
            run: "click",
        },
        {
    trigger: 'section[data-section="shared"] .o_article:contains("Shared Article") + .o_article:contains("Shared 2")',
    run: () => {
        dragAndDropArticle(
            'section[data-section="shared"] .o_article_name:contains("Shared 2")',
            'section[data-section="shared"] .o_article_name:contains("Shared Article")',
        );
    },
}, {
    // Check that the articles have been resequenced
    trigger: 'section[data-section="shared"] .o_article:contains("Shared 2") + .o_article:contains("Shared Article")',
},
// Drag and drop article above shared child
        {
            content: "Create a new article",
            trigger: "section[data-section=private]",
            run: "hover && click section[data-section=private] .o_section_create",
        },
        {
            trigger: '.o_article_active:contains("Untitled")',
        },
        {
    // Rename the article
    trigger: '.o_hierarchy_article_name > input',
    run: "edit Moved to Share && click body",
}, {
    trigger: '.o_article_active:contains("Moved to Share")',
    run: () => {
        dragAndDropArticle(
            'section[data-section="private"] .o_article_name:contains("Moved to Share")',
            'section[data-section="shared"] .o_article_name:contains("Shared Child")',
        );
    },
        },
        {
            content: "Moving under a shared article should ask for confirmation",
            trigger: '.modal .modal-footer .btn-primary',
            run: "click",
        },
        {
            trigger: 'section[data-section="private"]:not(:has(.o_article:contains("Moved to Share")))',
        },
        {
    // Check that the article has been moved
    trigger: 'section[data-section="shared"] .o_article .o_article:contains("Moved to Share")',
},
// Drag and drop shared child to shared
{
    trigger: '.o_knowledge_tree',
    run: () => {
        dragAndDropArticle(
            'section[data-section="shared"] .o_article_name:contains("Moved to Share")',
            'section[data-section="shared"] .o_article_name:contains("Shared Article")',
        );
    },
}, {
    // Check that the article moved and move it back
    trigger: 'section[data-section="shared"] .o_article:contains("Moved to Share") + .o_article:contains("Shared Article")',
    run: () => {
        dragAndDropArticle(
            'section[data-section="shared"] .o_article_name:contains("Moved to Share")',
            'section[data-section="shared"] .o_article_name:contains("Shared Article")',
        );
    },
        },
        {
            trigger: 'section[data-section="private"]:not(:has(.o_article:contains("Moved to Share")))',
        },
        {
    // Check that the article has been moved
    trigger: 'section[data-section="shared"] .o_article .o_article:contains("Moved to Share")',
},
// Drag and drop article to trash
{
    trigger: '.o_knowledge_tree',
    run: () => {
        dragAndDropArticle(
            'section[data-section="private"] .o_article_name:contains("Private Child 2")',
            '.o_section.o_knowledge_sidebar_trash',
        );
    },
}, {
    // Check that article has been removed from the sidebar
    trigger: '.o_knowledge_tree:not(:has(.o_article:contains("Private Child 2")))',
},
// Drag and drop parent of active article to trash
{
    trigger: '.o_article_active:contains("Moved to Share")',
    run: () => {
        dragAndDropArticle(
            'section[data-section="shared"] .o_article_name:contains("Shared Article")',
            '.o_section.o_knowledge_sidebar_trash',
        );
    },
}, {
    // Check that article has been removed from the sidebar
    trigger: '.o_knowledge_tree:not(:has(.o_article:contains("Shared Article")))',
}, {
    // Check that user has been redirected to first accessible article
    trigger: '.o_knowledge_tree .o_article:first:has(.o_article_active)',
},
// Resequence favorites
{
    trigger: 'section[data-section="favorites"] .o_article:contains("Private Article") + .o_article:contains("Workspace Child")',
    run: () => {
        dragAndDropArticle(
            'section[data-section="favorites"] .o_article_name:contains("Workspace Child")',
            'section[data-section="favorites"] .o_article_name:contains("Private Article")',
        );
    },
}, {
    // Check that favorites have been resequenced
    trigger: 'section[data-section="favorites"] .o_article:contains("Workspace Child") + .o_article:contains("Private Article")',
}]});
