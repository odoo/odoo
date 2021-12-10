/** @odoo-module */

import { Listener } from '@mail/model/model_listener';
import { followRelations } from '@mail/model/model_utils';

/**
 * Defines a set containing the relation records of the given field on the given
 * record. The behavior of this set depends on the field properties.
 */
export class RelationSet {

    /**
     * @param {mail.model} record
     * @param {ModelField} field
     */
    constructor(record, field) {
        this.record = record;
        this.field = field;
        this.set = new Set();
        if (this.field.sort) {
            this.sortArray = new Array();
            this.sortListenerByValue = new Map();
        }
    }

    /**
     * @returns {integer}
     */
    get size() {
        return this.set.size;
    }

    /**
     * @param {*} value
     */
    add(value) {
        if (this.set.has(value)) {
            return;
        }
        this.set.add(value);
        if (this.field.sort) {
            this.sortArray.push(value);
            const listener = new Listener({
                isPartOfUpdateCycle: true,
                name: `sort of ${value} in ${this.field} of ${this.record}`,
                onChange: info => {
                    // access all useful values of current record (and relations) to mark them as dependencies
                    this.record.modelManager.startListening(listener);
                    const compareDefinition = this.record[this.field.sort]();
                    const relatedPathSet = new Set(compareDefinition.map(operation => operation[1])); // only keep unique paths to avoid unnecessary listeners
                    for (const relatedPath of relatedPathSet) {
                        followRelations(value, relatedPath);
                    }
                    this.record.modelManager.stopListening(listener);
                    // sort outside of listening to avoid registering listeners for all other items (they already added their own listeners)
                    const compareFunction = (a, b) => {
                        for (const [compareMethod, relatedPath] of compareDefinition) {
                            const valA = followRelations(a, relatedPath);
                            const valB = followRelations(b, relatedPath);
                            switch (compareMethod) {
                                case 'defined-first': {
                                    if (!valA && !valB) {
                                        return 0;
                                    }
                                    if (!valA) {
                                        return 1;
                                    }
                                    if (!valB) {
                                        return -1;
                                    }
                                    break;
                                }
                                case 'case-insensitive-asc':
                                    if (valA.toLowerCase() === valB.toLowerCase()) {
                                        break;
                                    }
                                    return valA.toLowerCase() < valB.toLowerCase() ? -1 : 1;
                                case 'smaller-first':
                                    if (valA === valB) {
                                        break;
                                    }
                                    return valA - valB;
                                case 'greater-first':
                                    if (valA === valB) {
                                        break;
                                    }
                                    return valB - valA;
                                default:
                                    throw Error(`sort compare method "${compareMethod}" is not supported.`);
                            }
                        }
                        return 0;
                    };
                    // Naive method: re-sort the complete array every time. Ideally each item should
                    // be inserted/moved at its correct place immediately, but this can be optimized
                    // eventually if necessary.
                    this.sortArray.sort(compareFunction);
                    // Similarly naive approach: the field is marked as changed even if sort didn't
                    // actually move any record.
                    this.record.modelManager._markRecordFieldAsChanged(this.record, this.field);
                },
            });
            this.sortListenerByValue.set(value, listener);
            listener.onChange({ reason: 'initial call' });
        }
    }

    /**
     * Removes all elements.
     */
    clear() {
        for (const record of this.set) {
            this.delete(record);
        }
    }

    /**
     * @param {*} value
     * @returns {boolean} whether the value was present
     */
    delete(value) {
        const wasPresent = this.set.delete(value);
        if (!wasPresent) {
            return false;
        }
        if (this.field.sort) {
            // remove sort of current value
            const index = this.sortArray.indexOf(value);
            this.sortArray.splice(index, 1);
            // remove listener on current value
            const listener = this.sortListenerByValue.get(value);
            this.sortListenerByValue.delete(listener);
            this.record.modelManager.removeListener(listener);
        }
        return true;
    }

    /**
     * @param {*} value
     * @returns {boolean} whether the value is present
     */
    has(value) {
        return this.set.has(value);
    }

    /**
     * @returns {iterator}
     */
    [Symbol.iterator]() {
        if (this.field.sort) {
            return this.sortArray[Symbol.iterator]();
        }
        return this.set[Symbol.iterator]();
    }

}
