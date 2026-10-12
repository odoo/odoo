import {
    setTextCaretToEnd,
    computeTextElementSize,
} from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/utils/text";

export class TextEditHandler {
    constructor({ canvasRef, handles, floorPlanStore }) {
        this.canvasRef = canvasRef;
        this.handles = handles;
        this.floorPlanStore = floorPlanStore;
        this.operation = null;
    }

    isEditing(uuid) {
        if (!this.operation) {
            return false;
        }

        return this.operation.element.uuid === uuid;
    }

    startEdit(element, domElement) {
        // If already editing the same element, just refocus
        if (this.operation && this.operation.element.uuid === element.uuid) {
            this.initTextElement(domElement);
            return;
        }

        this.operation = {
            element,
            domElement,
            result: null,
        };

        setTimeout(() => {
            this.initTextElement(domElement);
        });
    }

    endEdit() {
        if (!this.operation) {
            return;
        }

        const { element } = this.operation;
        // Delete element if empty
        if (!element.text.trim().length) {
            this.floorPlanStore.removeElement(element.uuid);
        }
        this.operation = null;
    }

    initTextElement(domEl) {
        if (!domEl) {
            return;
        }
        const textEl = domEl.querySelector("[_text]");
        if (textEl) {
            this.operation.textEl = textEl;
            if (textEl.getAttribute["contenteditable"]) {
                textEl.focus();
                setTextCaretToEnd(textEl);
            }
        }
    }

    handleInput() {
        this.handleChange();
    }

    handleChange(props, options) {
        if (!this.operation) {
            return;
        }

        const { element, textEl } = this.operation;
        const result = { text: textEl.textContent };

        if (props) {
            //Update css to ensure correct styles are applied and measured
            textEl.style = element.getTextCssStyle(props);
            Object.assign(result, props);
            if (props.text) {
                textEl.textContent = props.text;
            }
        }

        const { top, left, width, height } = computeTextElementSize(textEl, element);

        result.width = width;
        result.height = height;
        result.left = left;
        result.top = top;
        this.floorPlanStore.updateElement(element.uuid, result, options);
    }

    /**
     * Handle paste event in text element - insert plain text only
     */
    handlePaste(event) {
        event.preventDefault();
        const text = (event.clipboardData || window.clipboardData).getData("text/plain");
        // Insert the plain text at the current cursor position
        const selection = window.getSelection();
        if (!selection.rangeCount) {
            return;
        }
        const range = selection.getRangeAt(0);
        range.deleteContents();
        const textNode = document.createTextNode(text);
        range.insertNode(textNode);
        range.setStartAfter(textNode);
        range.setEndAfter(textNode);
        selection.removeAllRanges();
        selection.addRange(range);

        event.target.dispatchEvent(new Event("input", { bubbles: true }));
    }
}
