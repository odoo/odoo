/** @odoo-module */

import { SORTABLE_TOLERANCE } from "@knowledge/components/sidebar/sidebar";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { queryOne, queryFirst } from "@odoo/hoot-dom";
import { childNodeIndex } from "@html_editor/utils/position";
import { Component, xml } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { ReadonlyEmbeddedViewComponent } from "@knowledge/editor/embedded_components/backend/view/readonly_embedded_view";

export const changeInternalPermission = (permission) => {
    const target = document.querySelector('.o_permission[aria-label="Internal Permission"]');
    target.value = permission;
    target.dispatchEvent(new Event("change"));
};

function getOffset(element) {
    if (!element.getClientRects().length) {
        return { top: 0, left: 0 };
    }

    const rect = element.getBoundingClientRect();
    const win = element.ownerDocument.defaultView;
    return {
        top: rect.top + win.pageYOffset,
        left: rect.left + win.pageXOffset,
    };
}

/**
 * Drag&drop an article in the sidebar
 * @param {MaybeIterable<Node> | string | null | undefined | false} from Hoot Dom target
 * @param {MaybeIterable<Node> | string | null | undefined | false} to Hoot Dom target
 */
export const dragAndDropArticle = (from, to) => {
    const source = queryOne(from);
    const target = queryOne(to);

    const elementOffset = getOffset(source);
    const targetOffset = getOffset(target);
    // If the target is under the element, the cursor needs to be in the upper
    // part of the target to trigger the move. If it is above, the cursor needs
    // to be in the bottom part.
    const targetY =
        targetOffset.top + (targetOffset.top > elementOffset.top ? target.offsetHeight - 1 : 0);

    const element = source.closest("li");
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
 * WARNING: This method uses the new editor powerBox.
 *
 * Steps to insert an articleLink for the given article, in the first editable
 * html_field found in the given container selector (should have a paragraph
 * as its last element, and the link will be inserted at the position at index
 * offset in the paragraph).
 *
 * @param {string} htmlFieldContainerSelector jquery selector for the container
 * @param {string} articleName name of the article to insert a link for
 * @param {integer} previousSiblingSelector jquery selector for the previous sibling of the article link
 * @returns {Array} tour steps
 */
export function appendArticleLink(htmlFieldContainerSelector, articleName, previousSiblingSelector = "") {
    return [{ // open the command bar
        trigger: `${htmlFieldContainerSelector} .odoo-editor-editable > p:last ${previousSiblingSelector}, ${htmlFieldContainerSelector} .odoo-editor-editable > div.o-paragraph:last ${previousSiblingSelector}`,
        run: function () {
            if (previousSiblingSelector) {
                openPowerbox(this.anchor.parentElement, this.anchor);
            } else {
                openPowerbox(this.anchor);
            }
        },
    }, { // click on the /article command
        trigger: '.o-we-powerbox .o-we-command .o-we-command-img.fa-newspaper-o',
        run: 'click',
    }, {
        // select an article in the list
        // 'not has span' is used to remove children articles as they also contain the article name
        trigger: `.o_select_menu_item > span:not(:has(span)):contains(${articleName})`,
        run: 'click',
    }, { // wait for the choice to be registered
        trigger: `.o_select_menu_toggler_slot:contains(${articleName})`,
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
        ...stepUtils.toggleHomeMenu(),
        {
            trigger: '.o_app[data-menu-xmlid="knowledge.knowledge_menu_root"]',
        }
    ];
}

export function makeVisible(selector) {
    const el = queryFirst(selector);
    if (el) {
        el.style.setProperty("visibility", "visible", "important");
        el.style.setProperty("opacity", "1", "important");
        el.style.setProperty("display", "block", "important");
    }
}

/**
 * WARNING: uses the legacy editor powerbox.
 *
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

/**
 * WARNING: uses the new editor powerbox.
 *
 * Opens the power box of the editor
 * @param {HTMLElement} paragraph
 * @param {Node} previousSibling previous sibling of the inserted element
 */
export function openPowerbox(paragraph, previousSibling) {
    let offset = 0;
    if (previousSibling) {
        offset = childNodeIndex(previousSibling) + 1;
    }
    const sel = document.getSelection();
    sel.removeAllRanges();
    const range = document.createRange();
    range.setStart(paragraph, offset);
    range.setEnd(paragraph, offset);
    sel.addRange(range);
    paragraph.dispatchEvent(
        new InputEvent("input", {
            inputType: "insertText",
            data: "/",
            bubbles: true,
        })
    );
}

export class WithoutLazyLoading extends Component {
    static template = xml`<t t-slot="default"/>`;
    static props = ["*"];
}

export function embeddedViewPatchFunctions() {
    let unpatchEmbeddedView;
    return {
        before: () => {
            unpatchEmbeddedView = patch(ReadonlyEmbeddedViewComponent.components, {
                ...ReadonlyEmbeddedViewComponent.components,
                WithLazyLoading: WithoutLazyLoading,
            });
        },
        after: () => {
            unpatchEmbeddedView();
        },
    };
}
