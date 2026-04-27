/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { endKnowledgeTour, openCommandBar } from './knowledge_tour_utils';

registry.category("web_tour.tours").add('knowledge_embedded_view_filters_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
        // open Knowledge App
        trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
        run: "click",
    }, { // open the command bar
        trigger: '.odoo-editor-editable > p',
        run: function () {
            openCommandBar(this.anchor);
        },
    }, { // add embedded list view of article items
        trigger: '.o-we-command-name:contains("Item List")',
        run: "click",
    }, {
        trigger: '.btn-primary',
        run: "click",
    }, { // Check that we have 2 elements in the embedded view
        trigger: 'tbody tr.o_data_row:nth-child(2)',
    }, { // add a simple filter
        trigger: '.o_searchview_input_container input',
        run: "edit 1",
    }, {
        trigger: 'li#1',
        run: "click",
    }, { // Check that the filter is effective
        trigger: 'tbody:not(tr.o_data_row:nth-child(2))',
    }, { // Open the filtered article
        trigger: 'tbody > tr > td[name="display_name"]',
        run: "click",
    }, { // Wait for the article to be open
        trigger: '.o_hierarchy_article_name input:value("Child 1")',
    }, { // Go back via the breadcrumbs go back button
        trigger: '.o_knowledge_header i.oi-chevron-left',
        run: "click",
    }, { // Check that there is the filter in the searchBar
        trigger: '.o_searchview_input_container > div',
    }, { // Check that the filter is effective
        trigger: 'tbody:not(tr.o_data_row:nth-child(2))',
    }, ...endKnowledgeTour()]
});
