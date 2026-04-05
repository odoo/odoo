/** @odoo-module **/

function normalizeValue(value) {
    if (value === undefined || value === null) {
        return "";
    }
    return String(value);
}

export function isSameCollectionValue(left, right) {
    return normalizeValue(left) === normalizeValue(right);
}

export function normalizeCollectionItems(items = []) {
    return (items || []).map((item, index) => {
        if (typeof item === "string" || typeof item === "number") {
            return {
                key: `item-${index}`,
                label: String(item),
                value: item,
            };
        }
        const value = item.value ?? item.id ?? item.label ?? index;
        const label = item.label ?? String(value);
        return {
            ...item,
            key: item.key || item.id || `${normalizeValue(value)}-${index}`,
            label,
            value,
        };
    });
}

export function filterCollectionItems(items = [], query = "") {
    const normalizedQuery = String(query || "").trim().toLowerCase();
    if (!normalizedQuery) {
        return items;
    }
    return items.filter((item) => {
        const haystack = [item.label, item.value, item.description, item.keywords]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();
        return haystack.includes(normalizedQuery);
    });
}

export function groupCollectionItems(items = []) {
    const groups = [];
    const indexByKey = new Map();

    for (const item of items) {
        const groupLabel = item.group || "";
        const groupKey = groupLabel || "__default__";
        if (!indexByKey.has(groupKey)) {
            indexByKey.set(groupKey, groups.length);
            groups.push({
                key: groupKey,
                label: groupLabel || null,
                items: [],
            });
        }
        groups[indexByKey.get(groupKey)].items.push(item);
    }

    return groups;
}

export function firstEnabledItem(items = []) {
    return items.find((item) => !item.disabled) || null;
}

export function findCollectionItemByValue(items = [], value) {
    return items.find((item) => isSameCollectionValue(item.value, value)) || null;
}
