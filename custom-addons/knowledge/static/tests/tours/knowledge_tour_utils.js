/** @odoo-module */

import { SORTABLE_TOLERANCE } from "@knowledge/components/sidebar/sidebar";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { setSelection, boundariesIn } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { insertText } from "@web/../tests/utils";

export const changeInternalPermission = (permission) => {
    const target = document.querySelector('.o_permission[aria-label="Internal Permission"]');
    target.value = permission;
    target.dispatchEvent(new Event("change"));
};

/**
 * Drag&drop an article in the sidebar
 * @param {$.Element} element
 * @param {$.Element} target
 */
export const dragAndDropArticle = ($element, $target) => {
    const elementOffset = $element.offset();
    const targetOffset = $target.offset();
    // If the target is under the element, the cursor needs to be in the upper
    // part of the target to trigger the move. If it is above, the cursor needs
    // to be in the bottom part.
    const targetY = targetOffset.top + (targetOffset.top > elementOffset.top ? ($target.outerHeight() - 1) : 0); 

    const element = $element[0].closest("li");
    const target = $target[0];
    element.dispatchEvent(
        new PointerEvent("pointerdown", {
            bubbles: true,
            which: 1,
            clientX: elementOffset.right,
            clientY: elementOffset.top,
        })
    );

    // Initial movement starting the drag sequence
    element.dispatchEvent(
        new PointerEvent("pointermove", {
            bubbles: true,
            which: 1,
            clientX: elementOffset.right,
            clientY: elementOffset.top + SORTABLE_TOLERANCE,
        })
    );

    // Timeouts because sidebar onMove is debounced
    setTimeout(() => {
        target.dispatchEvent(
            new PointerEvent("pointermove", {
                bubbles: true,
                which: 1,
                clientX: targetOffset.right,
                clientY: targetY,
            })
        );

        setTimeout(() => {
            element.dispatchEvent(
                new PointerEvent("pointerup", {
                    bubbles: true,
                    which: 1,
                    clientX: targetOffset.right,
                    clientY: targetY,
                })
            );
        }, 200);
    }, 200);
};

/**
 * Steps to insert an articleLink for the given article, in the first editable
 * html_field found in the given container selector (should have a paragraph
 * as its last element, and the link will be inserted at the position at index
 * offset in the paragraph).
 *
 * @param {string} htmlFieldContainerSelector jquery selector for the container
 * @param {string} articleName name of the article to insert a link for
 * @param {integer} offset position of the command call in the paragraph
 * @returns {Array} tour steps
 */
export function appendArticleLink(htmlFieldContainerSelector, articleName, offset=0) {
    return [{ // open the command bar
        trigger: `${htmlFieldContainerSelector} .odoo-editor-editable > p:last-child`,
        run: function () {
            openCommandBar(this.$anchor[0], offset);
        },
    }, { // click on the /article command
        trigger: '.oe-powerbox-commandName:contains(Article)',
        run: 'click',
        in_modal: false,
    }, { // select an article in the list
        trigger: `.o_select_menu_item:contains(${articleName})`,
        run: 'click',
        in_modal: false,
    }, { // wait for the choice to be registered
        trigger: `.o_select_menu_toggler_slot:contains(${articleName})`,
        run: () => {},
    }, { // click on the "Insert Link" button
        trigger: '.modal-dialog:contains(Link an Article) .modal-footer button.btn-primary',
        run: 'click'
    }];
}

/**
 * Ensure that the tour does not end on the Knowledge form view by returning to
 * the home menu.
 */
export function endKnowledgeTour() {
    return [
        stepUtils.toggleHomeMenu(), {
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
            run: () => {},
        }
    ];
}

export function makeVisible(selector) {
    const el = document.querySelector(selector);
    if (el) {
        el.style.setProperty("visibility", "visible", "important");
        el.style.setProperty("opacity", "1", "important");
        el.style.setProperty("display", "block", "important");
    }
}

/**
 * Opens the power box of the editor
 * @param {HTMLElement} paragraph
 * @param {integer} offset position of the command call in the paragraph
 */
export function openCommandBar(paragraph, offset=0) {
    const sel = document.getSelection();
    sel.removeAllRanges();
    const range = document.createRange();
    range.setStart(paragraph, offset);
    range.setEnd(paragraph, offset);
    sel.addRange(range);
    paragraph.dispatchEvent(
        new KeyboardEvent("keydown", {
            key: "/",
        })
    );
    const slash = document.createTextNode("/");
    paragraph.prepend(slash);
    sel.removeAllRanges();
    range.setStart(slash, 1);
    range.setEnd(slash, 1);
    sel.addRange(range);
    paragraph.dispatchEvent(
        new InputEvent("input", {
            inputType: "insertText",
            data: "/",
            bubbles: true,
        })
    );
    paragraph.dispatchEvent(
        new KeyboardEvent("keyup", {
            key: "/",
        })
    );
}

export function createNewCommentSteps(text) {
    return [{
        // Select some text in the first paragraph
        trigger: '.note-editable p.to-select',
        run: function () {
            setSelection(...boundariesIn(this.$anchor[0]));
        }
    }, {
        // Trigger comment creation with the editor toolbar
        trigger: '.oe-toolbar div[id="comment-line"]',
    }, {
        trigger: '.o_knowledge_comments_popover, .o_knowledge_comment_box',
        run: () => {}
    }, {
        trigger: '.o_knowledge_comments_popover .o-mail-Composer-input, .o-mail-Composer-input',
        run: async () => {
            await insertText('.o-mail-Composer-input', text || 'Hello World');
        }
    }, {
        // Send comment
        trigger: '.o_knowledge_comments_popover .o-mail-Composer-send:not([disabled=""]), .o-mail-Composer-send:not([disabled=""])'
    }, {
        trigger: '.o_knowledge_comment_box[data-id] .o_knowledge_comment_small_ui img, .o_knowledge_comment_box[data-id]',
        run: () => {}
    }, {
        trigger: '.o_knowledge_comment_box[data-id] .o_knowledge_comment_small_ui img, .o_knowledge_comment_box[data-id]',
        run: function () {
            this.$anchor[0].querySelector('.o_knowledge_comment_small_ui img')?.click();
        }
    }, {
        trigger: `.o-mail-Thread :contains(${text || 'Hello World'})`,
        run: () => {}
    },];
}

export function answerThreadSteps(text) {
    return [
        {
            trigger: '.o_knowledge_comments_popover, .o_knowledge_comment_box',
        }, {
            trigger: '.o_knowledge_comments_popover .o-mail-Composer-input, .o-mail-Composer-input',
            run: async () => {
                await insertText('.o-mail-Composer-input', text || 'Hello World');
            }
        }, {
            // Send comment
            trigger: '.o_knowledge_comments_popover .o-mail-Composer-send:not([disabled=""]), .o-mail-Composer-send:not([disabled=""])'
        }, {
            trigger: `.o-mail-Thread :contains(${text || 'Hello World'})`,
            run: () => {}
        }, {
            trigger: '.note-editable'
        }, {
            trigger: '.o_knowledge_comment_box:not(.commenting)',
            run: () => {}
        }
    ];
}

export function resolveCommentSteps() {
    return [
        {
            trigger: '.o-mail-Message-actions',
            run: () => {
                makeVisible('.o-mail-Message-actions');
            }
        }, {// Resolve Thread
            trigger: 'button[name="closeThread"]'
        }
    ];
}
