const MAX_ITEMS = 50;

export class History {
    constructor() {
        this.reset();
    }

    reset() {
        this.items = [];
        this.index = -1;
    }

    add(item) {
        // If we are not at the end of the history, remove all forward items
        if (this.index < this.items.length - 1) {
            this.items = this.items.slice(0, this.index + 1);
        }
        this.items.push(item);
        if (this.items.length > MAX_ITEMS) {
            this.items.shift(); // Remove oldest item
        } else {
            this.index++;
        }
    }

    undo() {
        if (this.canUndo()) {
            const item = this.items[this.index];
            this.index--;
            return item;
        }
        return null;
    }

    redo() {
        if (this.canRedo()) {
            this.index++;
            return this.items[this.index];
        }
        return null;
    }

    canUndo() {
        return this.index >= 0;
    }
    canRedo() {
        return this.index < this.items.length - 1;
    }
}
