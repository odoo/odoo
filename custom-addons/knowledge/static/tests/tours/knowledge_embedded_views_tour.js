/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { endKnowledgeTour, openCommandBar } from './knowledge_tour_utils';

registry.category("web_tour.tours").add('knowledge_embedded_view_filters_tour', {
    test: true,
    url: '/web',
    steps: () => [stepUtils.showAppsMenuItem(), {
        // open Knowledge App
        trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
    }, { // open the command bar
        trigger: '.odoo-editor-editable > p',
        run: function () {
            openCommandBar(this.$anchor[0]);
        },
    }, { // add embedded list view of article items
        trigger: '.oe-powerbox-commandName:contains("Item List")'
    }, {
        trigger: '.btn-primary'
    }, { // Check that we have 2 elements in the embedded view
        trigger: 'tbody tr.o_data_row:nth-child(2)',
        run: () => {}
    }, { // add a simple filter
        trigger: '.o_searchview_input_container input',
        run: 'text 1'
    }, {
        trigger: 'li#1'
    }, { // Check that the filter is effective
        trigger: 'tbody:not(tr.o_data_row:nth-child(2))',
        run: () => {}
    }, { // Open the filtered article
        trigger: 'tbody > tr > td[name="display_name"]'
    }, { // Wait for the article to be open
        trigger: '.o_breadcrumb_article_name_container > span:contains("Child 1")',
        run: () => {}
    }, { // Open parent via the sidebar
        trigger: '.o_article_name:contains("EditorCommandsArticle")'
    }, { // Check that there is no filter in the searchBar
        trigger: '.o_searchview_input_container:not( > div)',
        run: () => {}
    }, { // Check that we have 2 elements in the embedded view
        trigger: 'tbody tr.o_data_row:nth-child(2)',
        run: () => {}
    }, { // Go back via the breadcrumb
        trigger: '.o_back_button'
    }, { // Check that there is the filter in the searchBar
        trigger: '.o_searchview_input_container > div',
        run: () => {}
    }, { // Check that the filter is effective
        trigger: 'tbody:not(tr.o_data_row:nth-child(2))',
        run: () => {}
    }, ...endKnowledgeTour()]
});
