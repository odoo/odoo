import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
const CONSOLE_COLOR = "#F5B427";

export const getStrNotes = (note) => {
    if (!note) {
        return "";
    }
    if (Array.isArray(note)) {
        return note.map((n) => (typeof n === "string" ? n : n.text)).join(", ");
    }
    if (typeof note === "string") {
        try {
            const parsed = JSON.parse(note);
            if (Array.isArray(parsed)) {
                return parsed.map((n) => (typeof n === "string" ? n : n.text)).join(", ");
            }
            return note;
        } catch (error) {
            logPosMessage(
                "OrderChange",
                "getStrNotes",
                "Error while parsing note, not valid JSON",
                CONSOLE_COLOR,
                [error]
            );
            return note;
        }
    }
    return "";
};

export const filterChangeByCategories = (categoryIdsSet, currentOrderChange, models, opts = {}) => {
    const matchesCategories = (productId) => {
        const product = models["product.product"].get(productId);
        const categoryIds = product.parentPosCategIds;
        for (const categoryId of categoryIds) {
            if (categoryIdsSet.has(categoryId)) {
                return true;
            }
        }
        return false;
    };

    const filterChanges = (changes) =>
        // Combo line uuids to have at least one child line in the given categories
        changes?.filter((change) =>
            change.combo_line_ids && change.combo_line_ids.length > 0
                ? change.combo_line_ids.some((child) => matchesCategories(child.product_id))
                : matchesCategories(change["product_id"])
        );

    return {
        addedQuantity: filterChanges(currentOrderChange["addedQuantity"]),
        removedQuantity: filterChanges(currentOrderChange["removedQuantity"]),
        noteUpdate: filterChanges(currentOrderChange["noteUpdate"]),
    };
};

const getProductPosCategories = (product) =>
    product?.pos_categ_ids?.length
        ? product.pos_categ_ids
        : product?.product_tmpl_id?.pos_categ_ids || [];

const getSmallestCategory = (categs) => {
    let minCateg = null;
    let minSeq = Infinity;
    for (const categ of categs) {
        const seq = categ.sequence ?? 0;
        if (!minCateg || seq < minSeq || (seq === minSeq && categ.id < minCateg.id)) {
            minSeq = seq;
            minCateg = categ;
        }
    }
    return minCateg;
};

// Combo lookup order is deliberately the opposite of receiptLineGrouper: the cart keeps a
// combo together under its parent's category, preparation tickets dispatch each child to
// its own category. Keep them apart.
const getLineCategoryInfo = (orderLine) => {
    const targetLine = orderLine.combo_parent_id || orderLine;
    let categs = getProductPosCategories(targetLine.product_id);
    if (!categs.length && orderLine.combo_parent_id) {
        categs = getProductPosCategories(orderLine.product_id);
    }
    const categ = getSmallestCategory(categs);
    return categ
        ? { sequence: categ.sequence ?? 0, id: categ.id }
        : { sequence: Infinity, id: Infinity };
};

export const receiptLineGrouper = {
    getGroup(orderLine) {
        if (!orderLine.config?.iface_group_by_categ) {
            return false;
        }
        let categs = getProductPosCategories(orderLine.product_id);
        if (!categs.length && orderLine.combo_parent_id) {
            categs = getProductPosCategories(orderLine.combo_parent_id.product_id);
        }
        const categ = getSmallestCategory(categs);
        return categ ? { index: categ.sequence ?? 0, name: categ.name, categ_id: categ.id } : false;
    },
};

export const sortLinesByCategory = (lines) => {
    const sortKeyMap = new Map(lines.map((line) => [line, getLineCategoryInfo(line)]));
    for (const line of lines) {
        if (!line.combo_line_ids?.length) {
            continue;
        }
        let comboKey = sortKeyMap.get(line);
        if (comboKey?.sequence === Infinity) {
            for (const child of line.combo_line_ids) {
                const childKey = sortKeyMap.get(child);
                if (
                    childKey &&
                    (childKey.sequence < comboKey.sequence ||
                        (childKey.sequence === comboKey.sequence && childKey.id < comboKey.id))
                ) {
                    comboKey = childKey;
                }
            }
            sortKeyMap.set(line, comboKey);
        }
        for (const child of line.combo_line_ids) {
            sortKeyMap.set(child, comboKey);
        }
    }
    return [...lines].sort((a, b) => {
        const infoA = sortKeyMap.get(a) || { sequence: Infinity, id: Infinity };
        const infoB = sortKeyMap.get(b) || { sequence: Infinity, id: Infinity };
        return infoA.sequence !== infoB.sequence
            ? infoA.sequence - infoB.sequence
            : infoA.id - infoB.id;
    });
};
