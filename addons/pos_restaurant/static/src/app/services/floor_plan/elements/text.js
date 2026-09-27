import { Decor } from "./decor";

export class Text extends Decor {
    constructor(data) {
        super(data);
        this.shape = "text";
    }

    onEdit(editing) {
        if (editing) {
            this.initialText = this.text; // avoid updating the contenteditable's text during active text updates
        }
        super.onEdit(editing);
        if (!editing) {
            this.initialText = null;
        }
    }

    get textEditing() {
        return this.editing;
    }

    isSideResizeAllowed() {
        return true;
    }

    isCornerResizeAllowed() {
        return !this.editing;
    }

    isVerticalResizeAllowed() {
        return false;
    }

    isResizeMaintainRatio() {
        return true;
    }

    get isText() {
        return true;
    }
}
