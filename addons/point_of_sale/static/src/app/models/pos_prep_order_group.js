import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";
import { getStrNotes } from "./utils/order_change";

/**
 * Preparation data for printers and preparation display will be computed here.
 * It will aggregate several orders in case of split orders.
 */
export class PosPrepOrderGroup extends Base {
    static pythonModel = "pos.prep.order.group";

    setup(vals) {
        super.setup(vals);

        // Print stack is used to reprint tickets if needed, the stack key is the
        // stringified category ids set.
        if (!this.uiState) {
            this.uiState = {
                printStack: {},
            };
        }
    }

    get categories() {
        const config = this.models["pos.config"].getFirst();
        return config.preparationCategories;
    }

    get prepLines() {
        return this.prep_order_ids.flatMap((po) => po.prep_line_ids);
    }

    get lines() {
        return this.pos_order_ids.flatMap((po) => po.lines);
    }

    /**
     * Changes are now computed on several orders at the same time, in case of a split order
     * a preparation line quantity can be splitted on two orderlines.
     *
     * In this case we don't want to have any changes.
     */
    get changes() {
        const preparationCategories = this.categories;
        const preparationLines = this.prepLines;
        const orderlines = this.lines;
        const existingQuantityStack = {};
        const changes = {
            quantity: 0,
            categoryCount: {},
            printerData: {
                addedQuantity: {},
                removedQuantity: {},
                noteUpdate: {},
            },
        };

        for (const prepLine of preparationLines) {
            const key = keyMaker(prepLine);

            if (!existingQuantityStack[key]) {
                existingQuantityStack[key] = {
                    quantity: 0,
                    preparationLines: [],
                };
            }

            existingQuantityStack[key].preparationLines.push(prepLine);
            existingQuantityStack[key].quantity += prepLine.quantity - prepLine.cancelled;
        }

        for (const orderline of orderlines) {
            const key = keyMaker(orderline);
            const product = orderline.product_id;
            const category = product.pos_categ_ids.find((c) => preparationCategories.has(c.id));

            if (!category) {
                orderline.setHasChange(false);
                continue;
            }

            if (existingQuantityStack[key]) {
                existingQuantityStack[key].quantity -= orderline.qty;
            }

            if (!existingQuantityStack[key] || existingQuantityStack[key].quantity < 0) {
                const qty = Math.abs(existingQuantityStack[key]?.quantity || orderline.qty);
                changes.quantity += qty;
                changes.printerData.addedQuantity[key] = dataMaker(orderline, qty);

                if (!changes.categoryCount[category.id]) {
                    changes.categoryCount[category.id] = {
                        name: category.name,
                        count: 0,
                    };
                }

                changes.categoryCount[category.id].count += qty;
                orderline.setHasChange(true);
                continue;
            }

            if (orderline.changeNote) {
                changes.printerData.noteUpdate[key] = dataMaker(orderline, 0);
                orderline.setHasChange(true);
                continue;
            }

            orderline.setHasChange(false);
        }

        for (const [key, data] of Object.entries(existingQuantityStack)) {
            if (data.quantity <= 0) {
                continue;
            }

            const line = data.preparationLines[0];
            const product = line.product_id;
            const category = product.pos_categ_ids.find((c) => preparationCategories.has(c.id));

            if (category) {
                if (!changes.categoryCount[category.id]) {
                    changes.categoryCount[category.id] = {
                        name: category.name,
                        count: 0,
                    };
                }

                changes.quantity -= data.quantity;
                changes.categoryCount[category.id].count -= data.quantity;
                changes.printerData.removedQuantity[key] = dataMaker(line, -data.quantity);
            }
        }

        changes.categoryCount = Object.values(changes.categoryCount);
        changes.printerData.addedQuantity = Object.values(changes.printerData.addedQuantity);
        changes.printerData.removedQuantity = Object.values(changes.printerData.removedQuantity);
        changes.printerData.noteUpdate = Object.values(changes.printerData.noteUpdate);

        if (changes.printerData.noteUpdate.length) {
            changes.categoryCount.push({
                count: changes.printerData.noteUpdate.length,
                name: _t("Note"),
            });
        }

        return changes;
    }

    /**
     * Data is generated per category set since each printer can have different
     * preparation categories. Also data are split between added, removed and note updates.
     *
     * If no changes are found for the given categories, the last printed data will be returned.
     */
    async generatePrinterData(order, opts = { categoryIdsSet: new Set() }) {
        const receiptsData = [];
        const idsString = Array.from(opts.categoryIdsSet).sort().join("-");
        const orderChange = this.getChanges({ categoryIdsSet: opts.categoryIdsSet });
        const orderData = order.getOrderData();
        const addedQuantity = orderChange.printerData.addedQuantity;
        const removedQuantity = orderChange.printerData.removedQuantity;
        const noteUpdate = orderChange.printerData.noteUpdate;
        const generateGroupedData = (data) => {
            const dataChanges = data.changes?.data;
            if (dataChanges && dataChanges.some((c) => c.group)) {
                const groupedData = dataChanges.reduce((acc, c) => {
                    const { name = "", index = -1 } = c.group || {};
                    if (!acc[name]) {
                        acc[name] = { name, index, data: [] };
                    }
                    acc[name].data.push(c);
                    return acc;
                }, {});
                data.changes.groupedData = Object.values(groupedData).sort(
                    (a, b) => a.index - b.index
                );
            }
            return data;
        };

        if (
            addedQuantity.length === 0 &&
            removedQuantity.length === 0 &&
            noteUpdate.length === 0 &&
            !orderChange.internal_note &&
            !orderChange.general_customer_note
        ) {
            const lastPrints = this.uiState.printStack[idsString];
            const data = lastPrints ? lastPrints[lastPrints.length - 1] : [];
            for (const printable of data) {
                printable.reprint = true;
            }
            return lastPrints ? lastPrints[lastPrints.length - 1] : [];
        }

        if (addedQuantity.length) {
            const orderDataNew = { ...orderData };
            orderDataNew.changes = {
                title: _t("NEW"),
                data: addedQuantity,
            };
            receiptsData.push(generateGroupedData(orderDataNew));
        }

        if (removedQuantity.length) {
            const orderDataCancelled = { ...orderData };
            orderDataCancelled.changes = {
                title: _t("CANCELLED"),
                data: removedQuantity,
            };
            receiptsData.push(generateGroupedData(orderDataCancelled));
        }

        if (noteUpdate.length) {
            const orderDataNoteUpdate = { ...orderData };
            const { noteUpdateTitle, printNoteUpdateData = true } = orderChange;
            orderDataNoteUpdate.changes = {
                title: noteUpdateTitle || _t("NOTE UPDATE"),
                data: printNoteUpdateData ? noteUpdate : [],
            };
            receiptsData.push(generateGroupedData(orderDataNoteUpdate));
            orderData.changes.noteUpdate = [];
        }

        if (orderChange.internal_note || orderChange.general_customer_note) {
            const orderDataNote = { ...orderData };
            orderDataNote.changes = { title: "", data: [] };
            receiptsData.push(generateGroupedData(orderDataNote));
        }

        if (!this.uiState.printStack[idsString]) {
            this.uiState.printStack[idsString] = [];
        }
        this.uiState.printStack[idsString].push(receiptsData);
        return receiptsData;
    }

    /**
     * PoS config can have several printers with different preparation categories.
     * This method allows to filter the changes for only the given categories.
     */
    getChanges(opts = {}) {
        const changes = this.changes;
        const addedQuantity = changes.printerData.addedQuantity.map((c) => c.data);
        const removedQuantity = changes.printerData.removedQuantity.map((c) => c.data);
        const noteUpdate = changes.printerData.noteUpdate.map((c) => c.data);
        const result = {
            ...changes,
            noteChange: false,
            printerData: {
                addedQuantity: addedQuantity,
                removedQuantity: removedQuantity,
                noteUpdate: noteUpdate,
            },
        };

        if (opts.order) {
            const order = opts.order;
            if (order.uiState.last_general_customer_note !== order.general_customer_note) {
                result.generalCustomerNote = order.general_customer_note;
                result.noteChange = true;
            }

            if (order.uiState.last_internal_note !== order.internal_note) {
                result.internalNote = order.internal_note;
                result.noteChange = true;
            }
        }

        if (opts.categoryIdsSet) {
            const matchesCategories = (change) => {
                const product = this.models["product.product"].get(change["product_id"]);
                const categoryIds = product.parentPosCategIds;
                for (const categoryId of categoryIds) {
                    if (opts.categoryIdsSet.has(categoryId)) {
                        return true;
                    }
                }
                return false;
            };

            const filterChanges = (changes) => {
                // Combo line uuids to have at least one child line in the given categories
                const validComboUuids = new Set(
                    changes
                        .filter((change) => change.combo_parent_uuid && matchesCategories(change))
                        .map((change) => change.combo_parent_uuid)
                );
                return changes.filter(
                    (change) =>
                        (change.isCombo && validComboUuids.has(change.uuid)) ||
                        (!change.isCombo && matchesCategories(change))
                );
            };

            Object.assign(result, {
                printerData: {
                    addedQuantity: filterChanges(addedQuantity),
                    removedQuantity: filterChanges(removedQuantity),
                    noteUpdate: filterChanges(noteUpdate),
                },
            });
        }

        return result;
    }

    /**
     * Update the prep order group according to the given order changes.
     * Used after printing the preparation ticket to update the prep lines.
     */
    updateLastOrderChange(opts = {}, originOrder) {
        if (opts.cancelled) {
            this.prep_order_ids?.forEach((po) =>
                po.prep_line_ids?.forEach((pl) => (pl.cancelled = pl.quantity))
            );
        } else {
            // We don't need to add note updates here since preparation display will always show
            // the latest notes from the order lines.
            const changes = this.changes;
            const allChanges = [
                ...changes.printerData.addedQuantity,
                ...changes.printerData.removedQuantity,
            ];

            let prepOrder = null;
            for (const change of allChanges) {
                const line = change.line;
                const data = change.data;

                if (data.quantity > 0) {
                    const order = (prepOrder ||= this.models["pos.prep.order"].create({
                        pos_order_id: originOrder,
                        prep_order_group_id: this,
                    }));

                    this.models["pos.prep.line"].create({
                        prep_order_id: order,
                        pos_order_line_id: line,
                        product_id: line.getProduct().id,
                        quantity: data.quantity,
                        cancelled: 0,
                        attribute_value_ids: line.attribute_value_ids,
                    });
                } else {
                    let toCancel = data.quantity;
                    const mainKey = keyMaker(line);
                    for (const prepLine of [...this.prepLines].reverse()) {
                        const key = keyMaker(prepLine);
                        if (key !== mainKey) {
                            continue;
                        }

                        const lineQty = prepLine.quantity - prepLine.cancelled;
                        const cancellable = Math.min(lineQty, -toCancel);
                        prepLine.cancelled += cancellable;
                        toCancel += cancellable;
                        if (toCancel >= 0) {
                            break;
                        }
                    }
                }
            }
        }

        // Update last known state to avoid re-sending changes
        originOrder.uiState.last_general_customer_note = originOrder.general_customer_note;
        originOrder.uiState.last_internal_note = originOrder.internal_note;
        originOrder.lines.map((line) => {
            line.setHasChange(false);
            line.uiState.last_internal_note = line.getNote() || "";
            line.uiState.last_customer_note = line.getCustomerNote() || "";
            line.uiState.savedQuantity = line.getQuantity();
        });
    }
}

const keyMaker = (line) => {
    const orderline = line.pos_order_line_id || line;
    const objectKey = {
        product_id: orderline.product_id.id,
        combo_parent_id: orderline.combo_parent_id?.id,
        combo_line_ids: orderline.combo_line_ids.map((c) => c.id).sort(),
        attribute_value_ids: orderline.attribute_value_ids.map((a) => a.id).sort(),
        note: orderline?.getNote?.() || "",
        customer_note: orderline?.getCustomerNote?.() || "",
    };
    return JSON.stringify(objectKey);
};

const dataMaker = (prepOrPosLine, quantity) => {
    const line = prepOrPosLine.pos_order_line_id || prepOrPosLine;
    const product = line.product_id;
    const attributes = line.attribute_value_ids || [];
    return {
        line: line,
        data: {
            basic_name: product.name,
            isCombo: Boolean(line.combo_line_ids?.length || line.combo_parent_id),
            product_id: product.id,
            attribute_value_names: attributes.map((a) => a.name),
            quantity: quantity,
            note: getStrNotes(line?.getNote?.() || false),
            customer_note: getStrNotes(line?.getCustomerNote?.() || false),
            pos_categ_id: product.pos_categ_ids[0]?.id || 0,
            pos_categ_sequence: product.pos_categ_ids[0]?.sequence || 0,
            group: line?.getCourse?.() || false,
        },
    };
};

registry.category("pos_available_models").add(PosPrepOrderGroup.pythonModel, PosPrepOrderGroup);
