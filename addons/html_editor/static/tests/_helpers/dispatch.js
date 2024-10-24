function dispatchTo(editor, resourceId, ...args) {
    (editor.resources[resourceId] || []).forEach((fn) => fn(...args));
}

export function dispatchNormalize(editor) {
    dispatchTo(editor, "normalize_handlers", editor.editable);
}

export function dispatchClean(editor) {
    dispatchTo(editor, "clean_handlers", editor.editable);
}

export function dispatchCleanForSave(editor, payload) {
    dispatchTo(editor, "clean_for_save_handlers", payload);
}
