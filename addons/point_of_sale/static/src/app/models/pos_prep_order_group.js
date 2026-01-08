import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";

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

    /**
     * Data is generated per category set since each printer can have different
     * preparation categories. Also data are split between added, removed and note updates.
     *
     * If no changes are found for the given categories, the last printed data will be returned.
     */
    async generatePrinterData(order, opts = { categoryIdsSet: new Set() }) {
        const receiptsData = [];
        const idsString = Array.from(opts.categoryIdsSet).sort().join("-");
        const orderChange = this.getChanges({ categoryIdsSet: opts.categoryIdsSet, order: order });
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
        const changes = opts.order.changes;
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
}

registry.category("pos_available_models").add(PosPrepOrderGroup.pythonModel, PosPrepOrderGroup);
