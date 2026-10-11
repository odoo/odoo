import { Plugin } from "@html_editor/plugin";

/**
 * Registers the undo/redo shortcuts declared by HistoryPlugin.
 *
 * Native undo cannot revert the content inserted through the editor (mentions,
 * emojis, canned responses, pasted content): it is only recorded in its own
 * history.
 */
export class UndoRedoShortcutPlugin extends Plugin {
    static id = "undoRedoShortcut";
    static dependencies = ["history"];

    setup() {
        const { undo, redo } = this.dependencies.history;
        this.addShortcut("control+z", undo);
        this.addShortcut("control+y", redo);
        this.addShortcut("control+shift+z", redo);
    }

    addShortcut(hotkey, run) {
        this._cleanups.push(
            this.services.hotkey.add(hotkey, run, {
                // the editable is not a valid hotkey target by default
                bypassEditableProtection: true,
                allowRepeat: true,
                // not bound to the UI active element of the editor creation
                global: true,
                // active element rather than target, to also work in a shadow root
                isAvailable: () =>
                    this.editable.contains(this.editable.getRootNode().activeElement),
            })
        );
    }
}
