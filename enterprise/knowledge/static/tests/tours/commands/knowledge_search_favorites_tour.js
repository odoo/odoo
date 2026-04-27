/** @odoo-module */

import { registry } from "@web/core/registry";
import { endKnowledgeTour, openCommandBar } from "../knowledge_tour_utils.js";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

/**
 * Verify that a filter is not duplicated and is properly maintained after
 * a round trip with the breadcrumbs.
 *
 * @param {String} kanban name of a kanban view in which records can be created
 * @param {String} filterName name of a favorite filter which is already present in the view
 * @returns {Array} steps
 */
// const validateFavoriteFilterPersistence = function(kanban, filterName) {
//     return [{
//         content: 'create and edit item in the kanban view',
//         trigger: `[data-embedded="view"] .o_kanban_view:contains(${kanban}) .o-kanban-button-new`,
// 	    run: "click",
//     }, {
//         content: 'Give the name to the item',
//         trigger: 'input#name_0',
//         run: "edit Item 1",
//     }, {
//         content: 'click on the edit button',
//         trigger: '.o_kanban_edit',
//         run: "click",
//     },
//     {
//         trigger: '.o_hierarchy_article_name input:value("Item 1")',
//     },
//     {
//         content: `go to the ${kanban} from the breadcrumb`,
//         trigger: '.o_knowledge_header i.oi-chevron-left',
//         run: "click",
//     }, {
//         // Open the favorite of the first kanban and check it's favorite
//         trigger: `.o_breadcrumb:contains('${kanban}')`,
//         run: function () {
//             const view = this.anchor.closest(
//                 '.o_kanban_view'
//             );
//             const searchMenuButton = view.querySelector(".o_searchview_dropdown_toggler");
//             searchMenuButton.click();
//         },
//     }, {
//         trigger: '.o_favorite_menu',
//         run: function () {
//             const favorites = this.anchor.querySelectorAll("span.dropdown-item");
//             if (favorites.length !== 1 || favorites[0].innerText !== filterName) {
//                 console.error(`Only one filter "(${filterName})" should be available`);
//             }
//         },
//     }]
// }; // TODO uncomment when OWL is ready

/**
 * Insert the Knowledge kanban view as an embedded view in article.
 *
 * @param {String} article article name
 * @returns {Array} steps
 */
const embedKnowledgeKanbanViewSteps = function (article) {
    return [{ // open the Knowledge App
        trigger: ".o_app[data-menu-xmlid='knowledge.knowledge_menu_root']",
        run: "click",
    }, { // click on the search menu
        trigger: "[role='menuitem']:contains(Search)",
        run: "click",
    }, { // toggle on the kanban view
        trigger: ".o_switch_view.o_kanban",
        run: "click",
    }, { // wait for the kanban view
        trigger: ".o_kanban_renderer",
    }, { // open action menu dropdown
        trigger: ".o_control_panel .o_cp_action_menus button",
        run: "click",
    }, { // click on the knowledge menu button
        trigger: ".dropdown-menu .dropdown-toggle:contains(Knowledge)",
        run: function () {
            this.anchor.dispatchEvent(new Event("mouseenter"));
        },
    }, { // click on insert view in article
        trigger: ".dropdown-menu .dropdown-item:contains('Insert view in article')",
        run: "click",
    }, { // embed in article
        trigger: `.modal-dialog td.o_field_cell:contains(${article})`,
        run: "click",
    }];
};

/**
 * Test favorite filters and use by default filters in embedded views in
 * Knowledge. Need an article with 2 named kanban embeds to work.
 *
 * @param {String} kanban1 name of the first kanban
 * @param {String} kanban2 name of the second kanban
 * @returns {Array} steps
 */
// const validateFavoriteFiltersSteps = function (kanban1, kanban2) {
//     return [{
//         content: 'Open the search panel menu',
//         trigger: `[data-embedded="view"] .o_control_panel:contains(${kanban1}) .o_searchview_dropdown_toggler`,
//         run: "click",
//     }, {
//         trigger: ".o_favorite_menu .o_add_favorite",
//         run: "click",
//     }, {
//         trigger: ".o_favorite_menu:contains(Favorites) input[type='text']",
//         run: "edit testFilter && click .o_favorite_menu",
//     }, {
//         // use by default
//         trigger: ".o_favorite_menu .o-checkbox label:contains(Default filter)",
//         run: "click",
//     }, {
//         trigger: ".o_favorite_menu .o_save_favorite",
//         run: "click",
//     },
//     ...stepUtils.toggleHomeMenu(),
//     {
//         // open the Knowledge App
//         trigger: ".o_app[data-menu-xmlid='knowledge.knowledge_menu_root']",
//         run: "click",
//     }, {
//         // check that the search item has been added
//         trigger: ".o_facet_value",
//         run: function () {
//             const items = [...document.querySelectorAll(".o_searchview_facet")];
//             const testFacets = items.filter((el) => {
//                 return (
//                     el.querySelector(".o_searchview_facet_label .fa-star") &&
//                     el.querySelector(".o_facet_values")?.innerText === "testFilter"
//                 );
//             });
//             if (testFacets.length !== 1) {
//                 console.error("The 'testFilter' facet should be applied only on the first view");
//             }
//         },
//     }, {
//         // Open the favorite of the second kanban and check it has no favorite
//         // (favorite are defined per view)
//         trigger: `.o_breadcrumb:contains('${kanban2}')`,
//         run: function () {
//             const view = this.anchor.closest(
//                 '.o_kanban_view'
//             );
//             const searchMenuButton = view.querySelector(".o_searchview_dropdown_toggler");
//             searchMenuButton.click();
//         },
//     }, {
//         trigger: ".o_favorite_menu",
//         run: function () {
//             const items = document.querySelectorAll(".o_favorite_menu .dropdown-item");
//             if (items.length !== 1 || items[0].innerText !== "Save current search") {
//                 console.error("The favorite should not be available for the second view");
//             }
//         },
//     }];
// }; // TODO uncomment when OWL is ready

registry.category("web_tour.tours").add("knowledge_items_search_favorites_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            // open the Knowledge App
            trigger: ".o_app[data-menu-xmlid='knowledge.knowledge_menu_root']",
            run: "click",
        },
        {
            trigger: ".o_field_html",
            run: function () {
                const header = document.querySelector(".o_hierarchy_article_name input");
                if (header.value !== "Article 1") {
                    console.error(`Wrong article: ${header.value}`);
                }
            },
        },
        // Create the first Kanban
        {
            trigger: ".odoo-editor-editable > h1",
            run: function () {
                openCommandBar(this.anchor);
            },
        },
        {
            trigger: ".o-we-command-name:contains('Item Kanban')",
            run: "click",
        },
        {
            trigger: ".modal-body input.form-control",
            run: "edit Items 1",
        },
        {
            trigger: "button:contains('Insert')",
            run: "click",
        },
        // wait for kanban 1 to be inserted
        {
            trigger: "[data-embedded='view'] .o_control_panel:contains(Items 1)",
        },
        // Create the second Kanban
        {
            trigger: ".odoo-editor-editable > h1",
            run: function () {
                openCommandBar(this.anchor);
            },
        },
        {
            trigger: ".o-we-command-name:contains('Item Kanban')",
            run: "click",
        },
        {
            trigger: ".modal-body input.form-control",
            run: "edit Items 2",
        },
        {
            trigger: "button:contains('Insert')",
            run: "click",
        },
        // wait for kanban 2 to be inserted
        {
            trigger: "[data-embedded='view'] .o_control_panel:contains(Items 2)",
        },
        // ...validateFavoriteFiltersSteps("Items 1", "Items 2"), // TODO remove comment when OWL is good
        // testFilter was added as a favorite during validateFavoriteFiltersSteps to Items 1
        // ...validateFavoriteFilterPersistence("Items 1", "testFilter"), // TODO remove comment when OWL is good
        ...endKnowledgeTour(),
    ],
});

registry.category("web_tour.tours").add("knowledge_search_favorites_tour", {
    url: "/odoo",
    steps: () => [stepUtils.showAppsMenuItem(),
        // insert a first kanban view
        ...embedKnowledgeKanbanViewSteps("Article 1"),
        { // wait for embedded view to load and click on rename button
            trigger:
                "[data-embedded='view']:has( .o_control_panel:contains(Articles)) .o_control_panel_breadcrumbs_actions .dropdown-toggle",
            run: "click",
        }, {
            trigger: '.dropdown-item:contains(Edit)',
            run: "click",
        }, { // rename the view Kanban 1
            trigger: '.modal-dialog input.form-control',
            run: `edit Kanban 1`,
        }, { // click on rename
            trigger: "button:contains('Rename')",
            run: "click",
        }, { // check the application of the rename
            trigger: '[data-embedded="view"] .o_control_panel:contains(Kanban 1)',
        },
        ...stepUtils.toggleHomeMenu(),
        // insert a second kanban view
        ...embedKnowledgeKanbanViewSteps("Article 1"),
        { // wait for embedded view to load
            trigger: '[data-embedded="view"] .o_control_panel:contains(Articles)',
        },
        // ...validateFavoriteFiltersSteps("Kanban 1", "Articles"),
        ...endKnowledgeTour(),
    ],
});
