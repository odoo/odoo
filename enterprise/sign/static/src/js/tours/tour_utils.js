/** @odoo-module **/

import { queryFirst } from "@odoo/hoot-dom";

/**
 * Helper function that triggers a custom drag event with specified data properties.
 *
 * @param {HTMLElement} element - The element to trigger the event on
 * @param {string} type - The drag event type ('dragstart', 'drop', 'dragend')
 * @param {Object} data - Additional data to attach to the event (e.g., dataTransfer)
 */
function triggerDragEvent(element, type, data = {}) {
    const event = new DragEvent(type, { bubbles: true });
    for (const key in data) {
        Object.defineProperty(event, key, {
            value: data[key],
        });
    }
    element.dispatchEvent(event);
}

/**
 * Performs a drag and drop operation from a source element to a specific position
 * within an iframe containing PDF.js content. This function addresses the limitations
 * of Odoo's default tour drag_and_drop action which doesn't work properly with
 * iframe content controlled by PDF.js.
 *
 * The function creates a mock dataTransfer object to simulate real drag events
 * and calculates precise drop coordinates considering iframe scroll and page dimensions.
 *
 * @param {HTMLElement} from - The source element to drag from (e.g., signature button)
 * @param {number} height - Vertical position as fraction of page height (0.0-1.0, default: 0.5)
 * @param {number} width - Horizontal position as fraction of page width (0.0-1.0, default: 0.5)
 * @param {number} pageNumber - The target page number in the PDF (default: 1)
 */
function dragAndDropSignItemAtHeight(from, height = 0.5, width = 0.5, pageNumber = 1) {
    const iframe = document.querySelector("iframe");
    const to = queryFirst(`:iframe .page[data-page-number="${pageNumber}"]`);
    const toPosition = to.getBoundingClientRect();
    toPosition.x += iframe.contentWindow.scrollX + to.clientWidth * width;
    toPosition.y += iframe.contentWindow.scrollY + to.clientHeight * height;

    const dataTransferObject = {};
    const dataTransferMock = {
        setData: (key, value) => {
            dataTransferObject[key] = value;
        },
        getData: (key) => dataTransferObject[key],
        setDragImage: () => {},
        items: [],
    };

    triggerDragEvent(from, "dragstart", {
        dataTransfer: dataTransferMock,
    });

    triggerDragEvent(to, "drop", {
        pageX: toPosition.x,
        pageY: toPosition.y,
        dataTransfer: dataTransferMock,
    });

    triggerDragEvent(from, "dragend");
}

export default {
    dragAndDropSignItemAtHeight,
};
