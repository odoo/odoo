export class StyleInfoMap extends Map {
    get(key, insert = true) {
        if (insert && !this.has(key)) {
            this.set(key, new StyleInfo());
        }
        return super.get(key);
    }
    assign(source, key) {
        const styleInfo = this.get(key);
        styleInfo.merge(StyleInfo.from(source), styleInfo.maxSequence);
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

    dirty = true;
    sortedEntries = null;
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
    set(key, value) {
        this.dirty = true;
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
        this.dirty = true;
        return super.delete(...arguments);
    }
    clear() {
        this.dirty = true;
        return super.clear(...arguments);
    }
    /**
     * Merge the provided styleInfo assuming the provided
     * properties take precedence at equal sequence and importance
     *
     * @param {StyleInfo} styleInfo
     * @param {number} [sequence]
     */
    merge(styleInfo, sequence) {
        for (const [propertyName, propertyInfo] of styleInfo) {
            const thisPriority = this.getPropertyPriority(propertyName);
            const thisSequence = this.getPropertySequence(propertyName);
            const priority = styleInfo.getPropertyPriority(propertyName);
            sequence =
                sequence !== undefined ? sequence : styleInfo.getPropertySequence(propertyName);
            if (
                !this.has(propertyName) ||
                (priority && !thisPriority) ||
                (priority === thisPriority && sequence >= thisSequence)
            ) {
                this.set(
                    propertyName,
                    Object.assign(new PropertyInfo(), propertyInfo, {
                        sequence,
                    })
                );
            }
        }
        return this;
    }
    getSortedEntries() {
        if (this.dirty || !this.sortedEntries) {
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
            this.dirty = false;
        }
        return this.sortedEntries;
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
