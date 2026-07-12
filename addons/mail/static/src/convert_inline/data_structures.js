export class UniqueArray {
    array = [];
    set = new Set();

    constructor(iterable) {
        for (const item of iterable ?? []) {
            this.set.add(item);
        }
        this.array.push(...this.set);
    }

    get length() {
        return this.array.length;
    }

    at(index) {
        return this.array.at(index);
    }

    push(...items) {
        const newItemSet = new Set();
        const newItemArray = [];
        for (const item of items) {
            newItemSet.add(item);
            newItemArray.push(item);
            this.set.add(item);
        }
        this.array = this.array.filter((item) => !newItemSet.has(item)).concat(newItemArray);
        return this.array.length;
    }

    pop() {
        const length = this.array.length;
        const deleted = this.array.pop();
        if (this.array.length !== length) {
            this.set.delete(deleted);
        }
        return deleted;
    }

    splice(start, deleteCount, ...items) {
        const deleted = this.array.splice(start, deleteCount, ...items);
        for (const item of deleted) {
            this.set.delete(item);
        }
        for (const item of items) {
            this.set.add(item);
        }
        return deleted;
    }

    unshift(...items) {
        const newItemSet = new Set();
        const newItemArray = [];
        for (const item of items) {
            newItemSet.add(item);
            newItemArray.push(item);
            this.set.add(item);
        }
        this.array = newItemArray.concat(this.array.filter((item) => !newItemSet.has(item)));
        return this.array.length;
    }

    indexOf(item) {
        if (this.has(item)) {
            return this.array.indexOf(item);
        }
        return -1;
    }

    shift() {
        const length = this.array.length;
        const deleted = this.array.shift();
        if (this.array.length !== length) {
            this.set.delete(deleted);
        }
        return deleted;
    }

    has(item) {
        return this.set.has(item);
    }

    delete(item) {
        if (!this.set.has(item)) {
            return false;
        }
        this.set.delete(item);
        const index = this.array.indexOf(item);
        this.array.splice(index, 1);
        return true;
    }

    values() {
        return this.array.values();
    }

    map(callbackFn, thisArg) {
        return this.array.map(callbackFn, thisArg);
    }

    [Symbol.iterator]() {
        return this.array[Symbol.iterator]();
    }
}

export class ArrayMap extends Map {
    get(key, insert = true) {
        if (insert && !this.has(key)) {
            this.set(key, []);
        }
        return super.get(key);
    }
    concat(source, key) {
        this.get(key).push(...source);
    }
}

export class ObjectMap extends Map {
    get(key, insert = true) {
        if (insert && !this.has(key)) {
            this.set(key, {});
        }
        return super.get(key);
    }
    assign(source, key) {
        return Object.assign(this.get(key), source);
    }
}

export class SetMap extends Map {
    stringSeparator = " ";
    get(key, insert = true) {
        if (insert && !this.has(key)) {
            this.set(key, new Set());
        }
        return super.get(key);
    }
    union(iterable, key) {
        return this.applySetOperation(iterable, key, "union");
    }
    intersection(iterable, key) {
        return this.applySetOperation(iterable, key, "intersection");
    }
    difference(iterable, key) {
        return this.applySetOperation(iterable, key, "difference");
    }
    applySetOperation(iterable, key, operation) {
        if (typeof iterable === "string") {
            iterable = iterable.split(this.stringSeparator).filter(Boolean);
        }
        return this.set(key, this.get(key)[operation](new Set(iterable)));
    }
}
