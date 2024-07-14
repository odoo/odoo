/** @odoo-module */

/**
 * Knowledge history tour.
 * Features tested:
 * - Create / edit an article an ensure revisions are created on write
 * - Open the history dialog and check that the revisions are correctly shown
 * - Select a revision and check that the content / comparison are correct
 * - Click the restore button and check that the content is correctly restored
 */

import { endKnowledgeTour } from '@knowledge/../tests/tours/knowledge_tour_utils';
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const testArticleName = 'Test history Article';
function changeArticleContentAndSave(newContent) {
    return [ {
        // change the content of the article
        trigger: '.note-editable.odoo-editor-editable h1',
        run: 'text ' + newContent,  // modify the article content
    }, {
        // reload knowledge articles to make sure that the article is saved
        trigger: 'a[data-menu-xmlid="knowledge.knowledge_menu_home"]',
    }, {
        // wait for the page to reload and OWL to accept value change
        trigger: '.o_article:contains("' + testArticleName + '"):not(.o_article_active)',
        run: async () => {
            await new Promise((r) => setTimeout(r, 300));
        },
    }, {
        // click on the test article
        trigger: '.o_article:contains("' + testArticleName + '") a.o_article_name',
    }, {
        // wait for the article to be loaded
        trigger: '.o_article_active:contains("' + testArticleName + '") ',
        run: () => {},
    }];
}


registry.category("web_tour.tours").add('knowledge_history_tour', {
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
    },
        ...changeArticleContentAndSave(testArticleName),
        ...changeArticleContentAndSave('Modified Title 01'),
        ...changeArticleContentAndSave('Modified Title 02'),
        ...changeArticleContentAndSave('Modified Title 03'),
    {
        // Open history dialog
        trigger: '.btn.btn-history',
    }, {
        // check the history dialog is opened
        trigger: '.modal-header:contains("History")',
    }, {
        // check that we have the correct number of revision (4)
        trigger: ".html-history-dialog .revision-list .btn",
        run: function () {
            const items = document.querySelectorAll(".revision-list .btn");
            if (items.length !== 4) {
                throw new Error('Expect 4 Revisions in the history dialog, got ' + items.length);
            }
        },
    }, {
        // check the first revision content is correct
        trigger: '#history-content-tab:contains("Modified Title 02")',
    }, {
        // click on the 3rd revision
        trigger: '.html-history-dialog .revision-list .btn:nth-child(3)',
    }, {
        // check the 3rd revision content is correct
        trigger: '#history-content-tab:contains("' + testArticleName + '")',
    }, {
        // click on the comparison tab
        trigger: '#history-comparison',
    }, {
        // check the comparison content is correct
        trigger: '#history-comparison-tab',
        run: function () {
            const comparaisonHtml = document.querySelector('#history-comparison-tab').innerHTML;
            const correctHtml = '<h1><added>' + testArticleName + '</added><removed>Modified Title 03</removed></h1>';
            if (comparaisonHtml !== correctHtml) {
                throw new Error('Expect comparison to be ' + correctHtml + ', got ' + comparaisonHtml);
            }
        }
    }, {
        // click on the restore button
        trigger: '.modal-footer .btn-primary:contains("Restore")',
    } , {
        // ensure the article content is restored
        trigger: '.note-editable.odoo-editor-editable h1:contains("' + testArticleName + '")',
    },
    ...endKnowledgeTour()
]});
