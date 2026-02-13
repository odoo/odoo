import { removeClass } from "@html_editor/utils/dom";

function dispatchTo(editor, resourceId, ...args) {
    (editor.resources[resourceId] || []).forEach((fn) => fn(...args));
}

function processThrough(editor, resourceId, item, ...args) {
    return editor.processThrough(resourceId, item, ...args);
}

export function dispatchNormalize(editor) {
    dispatchTo(editor, "normalize_handlers", editor.editable);
}

export function cleanHints(editor) {
    for (const element of editor.editable.querySelectorAll(".o-we-hint")) {
        removeClass(element, "o-we-hint");
        element.removeAttribute("o-we-hint-text");
    }
}

export function processThroughCleanForSave(editor, item, options) {
    return processThrough(editor, "clean_for_save_processors", item, options);
}
