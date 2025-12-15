import { Plugin } from "../plugin";

/**
 * @typedef {((ev: InputEvent) => void)[]} on_beforeinput_handlers
 * @typedef {((ev: InputEvent) => void)[]} on_input_handlers
 */

export class InputPlugin extends Plugin {
    static id = "input";
    static dependencies = ["history", "selection"];
    setup() {
        this.addDomListener(this.editable, "beforeinput", this.onBeforeInput);
        this.addDomListener(this.editable, "keydown", this.onKeyDown);
        this.addDomListener(this.editable, "input", this.onInput);
    }

    onKeyDown(ev) {
        const selection = this.document.getSelection();
        // Some virtual keyboards (e.g. MS SwiftKey) fire keydown events with
        // key === "Unidentified" before a `beforeinput` event. At that point,
        // `document.getSelection()` reflects the correct caret position, but
        // by the time `beforeinput` fires, the selection has already been
        // moved by the keyboard's internal processing — before the input is
        // actually applied to the DOM.
        //
        // To work around this, we snapshot the selection here in `keydown`
        // and store it as a cached selection so that the `beforeinput` handler
        // can use this snapshot instead of calling `getSelection()` itself.
        if (selection?.rangeCount && selection.isCollapsed && ev.key === "Unidentified") {
            const range = selection.getRangeAt(0);
            this.dependencies.selection.setCachedSelection({
                anchorNode: selection.anchorNode,
                anchorOffset: selection.anchorOffset,
                focusNode: selection.focusNode,
                focusOffset: selection.focusOffset,
                rangeCount: 1,
                isCollapsed: selection.isCollapsed,
                getRangeAt: () => range.cloneRange(),
            });
        }
    }

    onBeforeInput(ev) {
        this.dependencies.selection.stageSelection();
        this.trigger("on_beforeinput_handlers", ev);
        this.dependencies.selection.setCachedSelection(null);
    }

    onInput(ev) {
        this.dependencies.history.commit({ batchable: ev.inputType === "insertText" });
        this.trigger("on_input_handlers", ev);
    }
}
