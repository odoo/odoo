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

export const filterChangeByCategories = (categoryIdsSet, currentOrderChange, models) => {
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
                ? change.combo_line_ids.some((child) => matchesCategories(child.product_id.id))
                : matchesCategories(change["product_id"])
        );

    return {
        addedQuantity: filterChanges(currentOrderChange["addedQuantity"]),
        removedQuantity: filterChanges(currentOrderChange["removedQuantity"]),
        noteUpdate: filterChanges(currentOrderChange["noteUpdate"]),
    };
};
