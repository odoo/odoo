/** @odoo-module */

import { dragAndDropArticle, endKnowledgeTour } from './knowledge_tour_utils.js';
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('knowledge_properties_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    // open Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
    run: "click",
}, { // ensure display of ParentArticle child articles
    trigger: '.o_article_handle:contains("ParentArticle") .o_article_caret',
    run: function (actions) {
        if (this.anchor.querySelector("i.fa-caret-right")) {
            actions.click();
        }
    }
}, { // go to ChildArticle
    trigger: '.o_article .o_article_name:contains("ChildArticle")',
    run: 'click',
}, { // wait ChildArticle loading
    trigger: '.o_hierarchy_article_name input:value("ChildArticle")',
}, { // click on add properties button in dropdown
    trigger: '#dropdown_tools_panel',
    run: 'click',
}, {
    trigger: 'button.o_knowledge_add_properties',
    run: 'click',
}, {
    trigger: '.o_field_property_add button',
    run: 'click'
}, { // modify property name
    trigger: '.o_field_property_definition_header',
    run: "edit myproperty && click body",
},
{
    trigger: '.o_field_property_label:contains("myproperty")',
},
{ // verify property and finish property edition
    trigger: '.o_knowledge_editor .odoo-editor-editable',
    run: 'click',
}, { // go to InheritPropertiesArticle
    trigger: '.o_article .o_article_name:contains("InheritPropertiesArticle")',
    run: 'click',
}, { // wait InheritPropertiesArticle loading and move InheritPropertiesArticle under ParentArticle
    trigger: '.o_hierarchy_article_name input:value("InheritPropertiesArticle")',
    run: () => {
        dragAndDropArticle(
            '.o_article_handle:contains("InheritPropertiesArticle")',
            '.o_article_handle:contains("ChildArticle")',
        );
    },
}, { // verify property
    trigger: '.o_knowledge_properties .o_field_property_label:contains("myproperty")',
}, ...endKnowledgeTour()
]});
