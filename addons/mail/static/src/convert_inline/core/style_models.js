export class StyleInfoMap extends Map {
    get(key, insert = true) {
        if (insert && !this.has(key)) {
            this.set(key, new StyleInfo());
        }
        return super.get(key);
    }
    assign(source, key) {
        const styleInfo = this.get(key);
        styleInfo.merge(StyleInfo.from(source), { sequence: styleInfo.maxSequence });
        return styleInfo;
    }
}

export class PropertyInfo {
    constructor({ value, priority, sequence } = {}) {
        this.value = `${value}`;
        this.priority = priority;
        this.sequence = sequence;
    }
    toString() {
        const value = this.value ?? "";
        const priority = this.value && this.priority ? ` !${this.priority}` : "";
        return `${value}${priority}`;
    }
}

/**
 * Inline style representation of an email Element
 */
export class StyleInfo extends Map {
    static from(styleObject) {
        let entries;
        if (styleObject instanceof StyleInfo) {
            return styleObject;
        } else if (styleObject instanceof Map) {
            entries = styleObject.entries();
        } else {
            entries = Object.entries(styleObject);
        }
        const styleInfo = new StyleInfo();
        for (const [key, value] of entries) {
            styleInfo.set(key, value);
        }
        return styleInfo;
    }

    dirtySortedEntries = true;
    dirtyIndexByPropertyName = true;
    sortedEntries = null;
    indexByPropertyName = null;
    maxSequence = 0;
    getPropertyValue(propertyName) {
        return this.get(propertyName)?.value ?? "";
    }
    getPropertyPriority(propertyName) {
        return this.get(propertyName)?.priority ?? "";
    }
    // The sequence of a propertyInfo determines the order
    // of a property in the inline style string (lower = before)
    getPropertySequence(propertyName) {
        return this.get(propertyName)?.sequence ?? 0;
    }
    setProperty(propertyName, value, priority = "", sequence = 0) {
        return this.set(propertyName, {
            value,
            priority,
            sequence,
        });
    }
    removeProperty(propertyName) {
        return this.delete(propertyName);
    }
    _setDirty() {
        this.dirtySortedEntries = true;
        this.dirtyIndexByPropertyName = true;
    }
    set(key, value) {
        this._setDirty();
        if (typeof value === "string" || typeof value === "number") {
            value = { value };
        }
        value = new PropertyInfo(value);
        if (this.maxSequence < value.sequence) {
            this.maxSequence = value.sequence;
        }
        return super.set(key, value);
    }
    delete() {
        this._setDirty();
        return super.delete(...arguments);
    }
    clear() {
        this._setDirty();
        return super.clear(...arguments);
    }
    /**
     * Merge the provided styleInfo assuming the provided
     * properties take precedence at equal sequence and importance,
     * unless an index indicates the existing property comes later.
     *
     * @param {StyleInfo} styleInfo
     * @param {Object} options
     * @param {number} [options.sequence] incoming properties forced sequence
     * @param {number} [options.index] incoming properties relative index
     */
    merge(styleInfo, { sequence, index } = {}) {
        const indexByPropertyName = index !== undefined ? this.getIndexByPropertyName() : new Map();
        for (const [propertyName, propertyInfo] of styleInfo) {
            const thisPriority = this.getPropertyPriority(propertyName);
            const thisSequence = this.getPropertySequence(propertyName);
            const thisIndex = indexByPropertyName.get(propertyName);
            const priority = styleInfo.getPropertyPriority(propertyName);
            const propertySequence =
                sequence !== undefined ? sequence : styleInfo.getPropertySequence(propertyName);
            const winsTie =
                propertySequence > thisSequence ||
                (propertySequence === thisSequence &&
                    (index === undefined || thisIndex === undefined || index >= thisIndex));
            if (
                !this.has(propertyName) ||
                (priority && !thisPriority) ||
                (priority === thisPriority && winsTie)
            ) {
                this.set(
                    propertyName,
                    Object.assign(new PropertyInfo(propertyInfo), {
                        sequence: propertySequence,
                    })
                );
            }
        }
        return this;
    }
    getSortedEntries() {
        if (this.dirtySortedEntries || !this.sortedEntries) {
            // Sort styleInfo entries by sequence, so that style properties from
            // rules with higher specificity come at the end. This is necessary
            // because e.g. a longhand property with higher specificity should
            // overwrite what a shorthand property with lower specificity defines.
            // Example: in the final inline style, border-radius with sequence 1
            // should be written BEFORE border-top-left-radius with sequence 2.
            this.sortedEntries = [...this].sort(
                ([, propertyInfoA], [, propertyInfoB]) =>
                    propertyInfoA.sequence - propertyInfoB.sequence
            );
            this.dirtySortedEntries = false;
        }
        return this.sortedEntries;
    }
    getIndexByPropertyName() {
        if (this.dirtyIndexByPropertyName || !this.indexByPropertyName) {
            const indexByPropertyName = new Map();
            let entryIndex = 0;
            for (const [propertyName] of this) {
                indexByPropertyName.set(propertyName, entryIndex);
                entryIndex++;
            }
            this.indexByPropertyName = indexByPropertyName;
            this.dirtyIndexByPropertyName = false;
        }
        return this.indexByPropertyName;
    }
    serialize(separator) {
        return this.getSortedEntries()
            .filter((entry) => Boolean(entry[1]))
            .map((entry) => `${entry.join(":")};`)
            .join(separator);
    }
    toString() {
        return this.serialize("");
    }
    applyOnElement(element) {
        if (element?.nodeType !== Node.ELEMENT_NODE) {
            return;
        }
        for (const [propertyName] of this.getSortedEntries()) {
            element.style.setProperty(
                propertyName,
                this.getPropertyValue(propertyName),
                this.getPropertyPriority(propertyName)
            );
        }
    }
}

export class ComputedStyle {
    constructor(computedStyleProxy) {
        this.computedStyleProxy = computedStyleProxy;
    }
    getPropertyValue(propertyName) {
        return this.computedStyleProxy[propertyName];
    }
    getPropertyPriority() {
        return "";
    }
}
