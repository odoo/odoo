/** @odoo-module */

import { dragAndDropArticle } from '@knowledge/../tests/tours/knowledge_tour_utils';
import { endKnowledgeTour } from './knowledge_tour_utils.js';
import { registry } from "@web/core/registry";

// Checks that one can resequence children under a readonly parent

registry.category("web_tour.tours").add('knowledge_resequence_children_of_readonly_parent_tour', {
    test: true,
    steps: () => [
{ // check presence of parent article and unfold it
    trigger: '.o_article_active:contains(Readonly Parent) > a.o_article_caret',
    run: 'click',
}, { // check existence and order of children, and reorder children
    trigger: '.o_article_active:contains(Readonly Parent)',
    extra_trigger: '.o_article_has_children:has(li:nth-child(1):contains(Child 1)):has(li:nth-child(2):contains(Child 2))',
    run: function () {
        const children = this.$anchor[0].parentElement.querySelectorAll(".o_article_name");
        // move 2nd child above the first.
        dragAndDropArticle($(children[2]), $(children[1]));
    },
}, { // check that the children were correctly reordered, and try to make a root from one children
    trigger: '.o_article_active:contains(Readonly Parent)',
    extra_trigger: '.o_article_has_children:has(li:nth-child(1):contains(Child 2)):has(li:nth-child(2):contains(Child 1))',
    run: function () {
        const child1 = this.$anchor[0].parentElement.querySelectorAll(".o_article_name")[2]
        // move 1st child above parent.
        dragAndDropArticle($(child1), this.$anchor);
    },
}, { // check that the 1st child move was effective
    trigger: '.o_section:contains(Workspace):has(li:nth-child(1):contains(Child 1)):has(li:nth-child(2):contains(Readonly Parent))',
    run: () => {},
}, ...endKnowledgeTour()
]});
