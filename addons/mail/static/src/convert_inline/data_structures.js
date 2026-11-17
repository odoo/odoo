export class UniqueArray {
    array = [];
    set = new Set();

    constructor(iterable) {
        for (const item of iterable ?? []) {
            if (this.set.has(item)) {
                continue;
            }
            this.set.add(item);
            this.array.push(item);
        }
    }

    get length() {
        return this.array.length;
    }

    at(index) {
        return this.array.at(index);
    }

    filter(callbackFn, thisArg) {
        return this.array.filter(callbackFn, thisArg);
    }

    push(...items) {
        const newItemSet = new Set();
        const newItemArray = [];
        for (const item of items) {
            if (newItemSet.has(item)) {
                continue;
            }
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

    splice(...args) {
        const length = this.array.length;
        const start = Math.trunc(args[0]) || 0;
        const index = start < 0 ? Math.max(length + start, 0) : Math.min(start, length);
        const deleteCount =
            args.length === 1
                ? length - index
                : Math.min(Math.max(Math.trunc(args[1]) || 0, 0), length - index);
        const items = new Set(args.slice(2));
        const deleted = this.array.slice(index, index + deleteCount);
        this.array = [
            ...this.array.slice(0, index).filter((item) => !items.has(item)),
            ...items,
            ...this.array.slice(index + deleteCount).filter((item) => !items.has(item)),
        ];
        for (const item of deleted) {
            if (!items.has(item)) {
                this.set.delete(item);
            }
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
            if (newItemSet.has(item)) {
                continue;
            }
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

    flatMap(callbackFn, thisArg) {
        return this.array.flatMap(callbackFn, thisArg);
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
    stringSeparator = /\s+/;
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
