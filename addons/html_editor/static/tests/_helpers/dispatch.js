import { removeClass } from "@html_editor/utils/dom";

export function cleanHints(editor) {
    for (const element of editor.editable.querySelectorAll(".o-we-hint")) {
        removeClass(element, "o-we-hint");
        element.removeAttribute("o-we-hint-text");
    }
}

export function processThroughCleanForSave(editor, item, options) {
    return editor.processThrough("clean_for_save_processors", item, options);
}
