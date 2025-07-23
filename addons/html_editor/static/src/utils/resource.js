export const resourceSequenceSymbol = Symbol("resourceSequence");

export function withSequence(seqObj, object) {
    return {
        [resourceSequenceSymbol]: seqObj,
        object,
    };
}

export function sortListWithSequence(list) {
    const sortedSequenceItems = [];
    const sequenceMap = new Map();
    const baseItems = [];
    const childItems = [];

    for (const item of list) {
        if (!item[resourceSequenceSymbol]) {
            baseItems.push({
                weight: 0,
            });
        }
    }
    for (const item of childItems) {
        // const seq = item[resourceSequenceSymbol];
        sequenceMap.set(item.object, { before: [], after: [] });
    }
    const items = [];
    for (const item of sequenceItems) {
        const seq = item[resourceSequenceSymbol];
        if (seq.before) {
            sequenceMap.get(item.object).before.push(seq.before);
        }
        if (seq.after) {
            sequenceMap.get(item.object).after.push(seq.after);
        }
    }
    const sortedItems = [];
    for (const item of items) {
        sortedItems.push(...sequenceMap.get(item.object).before);
        sortedItems.push(item.object);
        sortedItems.push(...sequenceMap.get(item.object).after);
    }
}
