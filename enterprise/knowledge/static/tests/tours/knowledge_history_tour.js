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
import { htmlEditorVersions } from "@html_editor/html_migrations/html_migrations_utils";

const VERSIONS = htmlEditorVersions();
const CURRENT_VERSION = VERSIONS.at(-1);

const testArticleName = 'Test history Article';
function changeArticleContentAndSave(newContent) {
    return [ {
        // change the content of the article
        trigger: '.note-editable.odoo-editor-editable h1',
        run: `editor ${newContent}`,  // modify the article content
    }, {
        // reload knowledge articles to make sure that the article is saved
        trigger: 'a[data-menu-xmlid="knowledge.knowledge_menu_home"]',
        run: "click",
    }, {
        // wait for the page to reload and OWL to accept value change
        trigger: '.o_article:contains("' + testArticleName + '"):not(.o_article_active)',
        run: async () => {
            await new Promise((r) => setTimeout(r, 300));
        },
    }, {
        // click on the test article
        trigger: '.o_article:contains("' + testArticleName + '") a.o_article_name',
        run: "click",
    }, {
        // wait for the article to be loaded
        trigger: '.o_article_active:contains("' + testArticleName + '") ',
    }];
}


registry.category("web_tour.tours").add('knowledge_history_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
        // open Knowledge App
        trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
        run: "click",
    }, {
        // click on the main "New" action
        trigger: '.o_knowledge_header .btn:contains("New")',
        run: "click",
    }, {
        // check that the article is correctly created (private section)
        trigger: 'section[data-section="private"] .o_article .o_article_name:contains("Untitled")',
    },
        ...changeArticleContentAndSave(testArticleName),
        ...changeArticleContentAndSave('Modified Title 01'),
        ...changeArticleContentAndSave('Modified Title 02'),
        ...changeArticleContentAndSave('Modified Title 03'),
    {
        // Open history dialog
        trigger: '.btn.btn-history',
        run: "click",
    }, {
        // check the history dialog is opened
        trigger: '.modal-header:contains("History")',
        run: "click",
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
        trigger: '.history-container .tab-pane:contains("Modified Title 02")',
        run: "click",
    }, {
        // click on the 3rd revision
        trigger: '.html-history-dialog .revision-list .btn:nth-child(3)',
        run: "click",
    }, {
        // check the 3rd revision content is correct
        trigger: '.history-container .tab-pane:contains("' + testArticleName + '")',
        run: "click",
    }, {
        // click on the comparison tab
        trigger: '.history-container .nav-item:contains(Comparison) a',
        run: "click",
    }, {
        // check the comparison content is correct
        trigger: '.history-container .tab-pane',
        run: function () {
            const comparisonHtml = document.querySelector('.history-container .tab-pane .o_readonly').innerHTML;
            const correctHtml = `<h1 class="oe-hint" data-oe-version="${CURRENT_VERSION}"><added>` + testArticleName + '</added><removed>Modified Title 03</removed></h1>';
            if (comparisonHtml !== correctHtml) {
                throw new Error('Expect comparison to be ' + correctHtml + ', got ' + comparisonHtml);
            }
        }
    }, {
        // click on the restore button
        trigger: '.modal-footer .btn-primary:contains("Restore")',
        run: "click",
    } , {
        // ensure the article content is restored
        trigger: '.note-editable.odoo-editor-editable h1:contains("' + testArticleName + '")',
        run: "click",
    },
    ...endKnowledgeTour()
]});
