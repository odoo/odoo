import { Plugin } from "../plugin";
import { CTYPES } from "../utils/content_types";
import { getState, isFakeLineBreak, prepareUpdate } from "../utils/dom_state";
import { DIRECTIONS, leftPos, rightPos } from "../utils/position";

export class LineBreakPlugin extends Plugin {
    static dependencies = ["selection", "split"];
    static name = "line_break";
    static shared = ["insertLineBreakElement"];
    resources = {
        onBeforeInput: this.onBeforeInput.bind(this),
    };

    handleCommand(command, payload) {
        switch (command) {
            case "INSERT_LINEBREAK":
                this.insertLineBreak();
                break;
            case "INSERT_LINEBREAK_NODE":
                this.insertLineBreakNode(payload);
                break;
            case "INSERT_LINEBREAK_ELEMENT":
                this.insertLineBreakElement(payload);
                break;
        }
    }

    insertLineBreak() {
        let selection = this.shared.getEditableSelection();
        if (!selection.isCollapsed) {
            // @todo @phoenix collapseIfZWS is not tested
            // this.shared.collapseIfZWS();
            this.dispatch("RESET_TABLE_SELECTION");
            this.dispatch("DELETE_SELECTION");
            selection = this.shared.getEditableSelection();
        }

        const targetNode = selection.anchorNode;
        const targetOffset = selection.anchorOffset;

        this.insertLineBreakNode({ targetNode, targetOffset });
        this.dispatch("ADD_STEP");
    }
    insertLineBreakNode({ targetNode, targetOffset }) {
        if (targetNode.nodeType === Node.TEXT_NODE) {
            targetOffset = this.shared.splitTextNode(targetNode, targetOffset);
            targetNode = targetNode.parentElement;
        }

        for (const callback of this.getResource("handle_insert_line_break_element")) {
            if (callback({ targetNode, targetOffset })) {
                return;
            }
        }

        this.insertLineBreakElement({ targetNode, targetOffset });
    }

    insertLineBreakElement({ targetNode, targetOffset }) {
        const restore = prepareUpdate(targetNode, targetOffset);

        const brEl = this.document.createElement("br");
        const brEls = [brEl];
        if (targetOffset >= targetNode.childNodes.length) {
            targetNode.appendChild(brEl);
        } else {
            targetNode.insertBefore(brEl, targetNode.childNodes[targetOffset]);
        }
        if (
            isFakeLineBreak(brEl) &&
            getState(...leftPos(brEl), DIRECTIONS.LEFT).cType !== CTYPES.BR
        ) {
            const brEl2 = this.document.createElement("br");
            brEl.before(brEl2);
            brEls.unshift(brEl2);
        }

        restore();

        // @todo ask AGE about why this code was only needed for unbreakable.
        // See `this._applyCommand('oEnter') === UNBREAKABLE_ROLLBACK_CODE` in
        // web_editor. Because now we should have a strong handling of the link
        // selection with the link isolation, if we want to insert a BR outside,
        // we can move the cursor outside the link.
        // So if there is no reason to keep this code, we should remove it.
        //
        // const anchor = brEls[0].parentElement;
        // // @todo @phoenix should this case be handled by a LinkPlugin?
        // // @todo @phoenix Don't we want this for all spans ?
        // if (anchor.nodeName === "A" && brEls.includes(anchor.firstChild)) {
        //     brEls.forEach((br) => anchor.before(br));
        //     const pos = rightPos(brEls[brEls.length - 1]);
        //     this.shared.setSelection({ anchorNode: pos[0], anchorOffset: pos[1] });
        // } else if (anchor.nodeName === "A" && brEls.includes(anchor.lastChild)) {
        //     brEls.forEach((br) => anchor.after(br));
        //     const pos = rightPos(brEls[0]);
        //     this.shared.setSelection({ anchorNode: pos[0], anchorOffset: pos[1] });
        // }
        for (const el of brEls) {
            // @todo @phoenix we don t want to setSelection multiple times
            if (el.parentNode) {
                const pos = rightPos(el);
                this.shared.setSelection({ anchorNode: pos[0], anchorOffset: pos[1] });
                break;
            }
        }
    }

    onBeforeInput(e) {
        if (e.inputType === "insertLineBreak") {
            e.preventDefault();
            this.insertLineBreak();
        }
    }
}
