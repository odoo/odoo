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
const validateFavoriteFilterPersistence = function(kanban, filterName) {
    return [{
        content: 'create and edit item in the kanban view',
        trigger: `.o_knowledge_embedded_view .o_kanban_view:contains(${kanban}) .o-kanban-button-new`,
	    run: "click",
    }, {
        content: 'Give the name to the item',
        trigger: 'input#name_0',
        run: 'text Item 1',
    }, {
        content: 'click on the edit button',
        trigger: '.o_kanban_edit',
    }, {
        content: `go to the ${kanban} from the breadcrumb`,
        trigger: '.o_back_button',
    }, {
        // Open the favorite of the first kanban and check it's favorite
        trigger: `.o_breadcrumb:contains('${kanban}')`,
        run: function () {
            const view = this.$anchor[0].closest(
                '.o_kanban_view'
            );
            const searchMenuButton = view.querySelector(".o_searchview_dropdown_toggler");
            searchMenuButton.click();
        },
    }, {
        trigger: '.o_favorite_menu',
        run: function () {
            const favorites = this.$anchor[0].querySelectorAll("span.dropdown-item");
            if (favorites.length !== 1 || favorites[0].innerText !== filterName) {
                console.error(`Only one filter "(${filterName})" should be available`);
            }
        },
    }]
};

/**
 * Insert the Knowledge kanban view as an embedded view in article.
 *
 * @param {String} article article name
 * @returns {Array} steps
 */
const embedKnowledgeKanbanViewSteps = function (article) {
    return [{ // open the Knowledge App
        trigger: ".o_app[data-menu-xmlid='knowledge.knowledge_menu_root']",
    }, { // click on the search menu
        trigger: "[role='menuitem']:contains(Search)",
    }, { // toggle on the kanban view
        trigger: ".o_switch_view.o_kanban",
    }, { // wait for the kanban view
        trigger: ".o_kanban_renderer",
        run: () => {},
    }, { // open action menu dropdown
        trigger: ".o_control_panel .o_cp_action_menus button",
    }, { // click on the knowledge menu button
        trigger: ".o_control_panel .o_cp_action_menus .dropdown-toggle:contains(Knowledge)",
        run: function () {
            this.$anchor[0].dispatchEvent(new Event("mouseenter"));
        },
    }, { // click on insert view in article
        trigger: ".o_cp_action_menus span:contains('Insert view in article')",
    }, { // embed in article
        trigger: `.modal-dialog td.o_field_cell:contains(${article})`,
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
const validateFavoriteFiltersSteps = function (kanban1, kanban2) {
    return [{
        content: 'Open the search panel menu',
        trigger: `.o_knowledge_embedded_view .o_control_panel:contains(${kanban1}) .o_searchview_dropdown_toggler`,
    }, {
        trigger: ".o_favorite_menu .o_add_favorite",
    }, {
        trigger: ".o_favorite_menu:contains(Favorites) input[type='text']",
        run: "text testFilter",
    }, {
        // use by default
        trigger: ".o_favorite_menu .o-checkbox:contains(Default filter) input",
    }, {
        trigger: ".o_favorite_menu .o_save_favorite",
    },
    stepUtils.toggleHomeMenu(),
    {
        // open the Knowledge App
        trigger: ".o_app[data-menu-xmlid='knowledge.knowledge_menu_root']",
    }, {
        // check that the search item has been added
        trigger: ".o_facet_value",
        run: function () {
            const items = [...document.querySelectorAll(".o_searchview_facet")];
            const testFacets = items.filter((el) => {
                return (
                    el.querySelector(".o_searchview_facet_label .fa-star") &&
                    el.querySelector(".o_facet_values")?.innerText === "testFilter"
                );
            });
            if (testFacets.length !== 1) {
                console.error("The 'testFilter' facet should be applied only on the first view");
            }
        },
    }, {
        // Open the favorite of the second kanban and check it has no favorite
        // (favorite are defined per view)
        trigger: `.o_breadcrumb:contains('${kanban2}')`,
        run: function () {
            const view = this.$anchor[0].closest(
                '.o_kanban_view'
            );
            const searchMenuButton = view.querySelector(".o_searchview_dropdown_toggler");
            searchMenuButton.click();
        },
    }, {
        trigger: ".o_favorite_menu",
        run: function () {
            const items = document.querySelectorAll(".o_favorite_menu .dropdown-item");
            if (items.length !== 1 || items[0].innerText !== "Save current search") {
                console.error("The favorite should not be available for the second view");
            }
        },
    }];
};

registry.category("web_tour.tours").add("knowledge_items_search_favorites_tour", {
    url: "/web",
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            // open the Knowledge App
            trigger: ".o_app[data-menu-xmlid='knowledge.knowledge_menu_root']",
        },
        {
            trigger: ".o_field_html",
            run: function () {
                const header = document.querySelector(".o_breadcrumb_article_name input");
                if (header.value !== "Article 1") {
                    console.error(`Wrong article: ${header.value}`);
                }
            },
        },
        // Create the first Kanban
        {
            trigger: ".odoo-editor-editable > h1",
            run: function () {
                openCommandBar(this.$anchor[0]);
            },
        },
        {
            trigger: ".oe-powerbox-commandName:contains('Item Kanban')",
        },
        {
            trigger: ".modal-body input.form-control",
            run: "text Items 1",
        },
        {
            trigger: "button:contains('Insert')",
        },
        // wait for kanban 1 to be inserted
        {
            trigger: ".o_knowledge_embedded_view .o_control_panel:contains(Items 1)",
            run: () => {},
        },
        // Create the second Kanban
        {
            trigger: ".odoo-editor-editable > h1",
            run: function () {
                openCommandBar(this.$anchor[0]);
            },
        },
        {
            trigger: ".oe-powerbox-commandName:contains('Item Kanban')",
        },
        {
            trigger: ".modal-body input.form-control",
            run: "text Items 2",
        },
        {
            trigger: "button:contains('Insert')",
        },
        // wait for kanban 2 to be inserted
        {
            trigger: ".o_knowledge_embedded_view .o_control_panel:contains(Items 2)",
            run: () => {},
        },
        ...validateFavoriteFiltersSteps("Items 1", "Items 2"),
        // testFilter was added as a favorite during validateFavoriteFiltersSteps to Items 1
        ...validateFavoriteFilterPersistence("Items 1", "testFilter"),
        ...endKnowledgeTour(),
    ],
});

registry.category("web_tour.tours").add("knowledge_search_favorites_tour", {
    url: "/web",
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(),
        // insert a first kanban view
        ...embedKnowledgeKanbanViewSteps("Article 1"),
        { // wait for embedded view to load and click on rename button
            trigger: '.o_knowledge_behavior_type_embedded_view:has(.o_knowledge_embedded_view .o_control_panel:contains(Articles)) .o_control_panel_breadcrumbs_actions .dropdown-toggle',
            allowInvisible: true,
        }, {
            trigger: '.dropdown-item:contains(Edit)'
        }, { // rename the view Kanban 1
            trigger: '.modal-dialog input.form-control',
            run: `text Kanban 1`,
        }, { // click on rename
            trigger: "button:contains('Rename')",
        }, { // check the application of the rename
            trigger: '.o_knowledge_embedded_view .o_control_panel:contains(Kanban 1)',
            run: () => {},
        },
        stepUtils.toggleHomeMenu(),
        // insert a second kanban view
        ...embedKnowledgeKanbanViewSteps("Article 1"),
        { // wait for embedded view to load
            trigger: '.o_knowledge_embedded_view .o_control_panel:contains(Articles)',
            run: () => {},
        },
        ...validateFavoriteFiltersSteps("Kanban 1", "Articles"),
        ...endKnowledgeTour(),
    ],
});
