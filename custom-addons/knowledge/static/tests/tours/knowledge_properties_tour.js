/** @odoo-module */

import { dragAndDropArticle, endKnowledgeTour } from './knowledge_tour_utils.js';
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('knowledge_properties_tour', {
    test: true,
    url: '/web',
    steps: () => [stepUtils.showAppsMenuItem(), {
    // open Knowledge App
    trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
}, { // ensure display of ParentArticle child articles
    trigger: '.o_article_handle:contains("ParentArticle") .o_article_caret',
    run: function (actions) {
        const button = this.$anchor[0];
        if (button.querySelector('i.fa-caret-right')) {
            actions.click(this.$anchor);
        }
    }
}, { // go to ChildArticle
    trigger: '.o_article .o_article_name:contains("ChildArticle")',
    run: 'click',
}, { // wait ChildArticle loading
    trigger: '.breadcrumb .active:contains("ChildArticle")',
    run: () => {},
}, { // click on add properties
    trigger: 'button.o_knowledge_add_properties',
    run: 'click',
}, {
    trigger: '.o_field_property_add button',
    run: 'click'
}, { // modify property name
    trigger: '.o_field_property_definition_header',
    run: 'text_blur myproperty',
}, { // verify property and finish property edition
    trigger: '.o_knowledge_editor .odoo-editor-editable',
    extra_trigger: '.o_field_property_label:contains("myproperty")',
    run: 'click',
}, { // go to InheritPropertiesArticle
    trigger: '.o_article .o_article_name:contains("InheritPropertiesArticle")',
    run: 'click',
}, { // wait InheritPropertiesArticle loading and move InheritPropertiesArticle under ParentArticle
    trigger: '.breadcrumb .active:contains("InheritPropertiesArticle")',
    run: () => {
        dragAndDropArticle(
            $('.o_article_handle:contains("InheritPropertiesArticle")'),
            $('.o_article_handle:contains("ChildArticle")'),
        );
    },
}, { // verify property
    trigger: '.o_knowledge_properties .o_field_property_label:contains("myproperty")',
    run: () => {},
}, ...endKnowledgeTour()
]});
