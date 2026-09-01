export const changesToOrder = (order, orderPreparationCategories, cancelled = false) => {
    const toAdd = [];
    const toRemove = [];

    const orderChanges = getOrderChanges(order, orderPreparationCategories);
    const linesChanges = !cancelled
        ? Object.values(orderChanges.orderlines)
        : Object.values(order.last_order_preparation_change.lines);

    for (const lineChange of linesChanges) {
        if (lineChange["quantity"] > 0 && !cancelled) {
            toAdd.push(lineChange);
        } else {
            lineChange["quantity"] = Math.abs(lineChange["quantity"]); // we need always positive values.
            toRemove.push(lineChange);
        }
    }

    return {
        new: toAdd,
        cancelled: toRemove,
        noteUpdate: Object.values(orderChanges.noteUpdate),
        general_customer_note: orderChanges.general_customer_note,
        internal_note: orderChanges.internal_note,
    };
};

/**
 * @returns {{ [lineKey: string]: { product_id: number, name: string, note: string, quantity: number } }}
 * This function recalculates the information to be sent to the preparation tools,
 * it uses the variable last_order_preparation_change which contains the last changes sent
 * to perform this calculation.
 */
export const getOrderChanges = (order, orderPreparationCategories) => {
    const prepaCategoryIds = orderPreparationCategories;
    const oldChanges = order.last_order_preparation_change.lines;
    const changes = {};
    const noteUpdate = {};
    let changesCount = 0;
    let changeAbsCount = 0;

    const hasPreparationCategory = (product) => {
        if (!product) {
            return false;
        }
        return product.parentPosCategIds.some((id) => prepaCategoryIds.has(id));
    };

    // Compares the orderlines of the order with the last ones sent.
    // When one of them has changed, we add the change.
    for (const orderline of order.getOrderlines()) {
        const product = orderline.getProduct();
        const note = orderline.getNote();
        const customerNote = orderline.getCustomerNote();
        const lineKey = orderline.uuid;

        const hasPrepaCategory =
            hasPreparationCategory(product) ||
            hasPreparationCategory(orderline.combo_parent_id?.product_id) ||
            orderline.combo_line_ids?.some((line) => hasPreparationCategory(line.getProduct())) ||
            false;

        if (hasPrepaCategory) {
            const key = Object.keys(order.last_order_preparation_change.lines).find((k) =>
                k.startsWith(orderline.uuid)
            ); // find old data but note changed
            const quantity = orderline.getQuantity();

            const relatedKey = key !== lineKey ? key : lineKey; // if note update key would be different
            const quantityDiff =
                (oldChanges[relatedKey] ? quantity - oldChanges[relatedKey].quantity : quantity) ||
                0;
            const noteChange =
                oldChanges[relatedKey] &&
                (oldChanges[relatedKey].note !== note ||
                    oldChanges[relatedKey].customer_note !== customerNote);

            const lineDetails = {
                uuid: orderline.uuid,
                name: orderline.getFullProductName(),
                basic_name: orderline.product_id.name,
                isCombo: Boolean(orderline?.combo_line_ids?.length),
                combo_parent_uuid: orderline?.combo_parent_id?.uuid,
                product_id: product.id,
                attribute_value_names: orderline.attribute_value_ids.map((a) => a.name),
                quantity: quantityDiff,
                note: note,
                customer_note: customerNote,
                pos_categ_id: product.pos_categ_ids[0]?.id ?? 0,
                pos_categ_sequence: product.pos_categ_ids[0]?.sequence ?? 0,
                display_name: product.display_name,
                group: receiptLineGrouper.getGroup(orderline),
            };

            if (quantityDiff) {
                // if note update with qty add
                changes[lineKey] = lineDetails;
                changesCount += quantityDiff;
                changeAbsCount += Math.abs(quantityDiff);
                if (noteChange) {
                    lineDetails.quantity = oldChanges[relatedKey].quantity || 0;
                    noteUpdate[lineKey] = lineDetails;
                }

                orderline.setHasChange(true);
            } else {
                if (quantityDiff) {
                    orderline.setHasChange(false);
                } else {
                    // If only note updated
                    if (noteChange) {
                        lineDetails.quantity = orderline.qty;
                        noteUpdate[lineKey] = lineDetails;
                        orderline.setHasChange(true);
                        changesCount += 1;
                    } else {
                        orderline.setHasChange(false);
                    }
                }
            }
        } else {
            orderline.setHasChange(false);
        }
    }
    // Checks whether an orderline has been deleted from the order since it
    // was last sent to the preparation tools. If so we add this to the changes.
    for (const [lineKey, lineResume] of Object.entries(order.last_order_preparation_change.lines)) {
        if (!order.models["pos.order.line"].getBy("uuid", lineResume["uuid"])) {
            const quantity = isNaN(lineResume["quantity"]) ? 0 : lineResume["quantity"];
            if (!changes[lineKey]) {
                changes[lineKey] = {
                    uuid: lineResume["uuid"],
                    product_id: lineResume["product_id"],
                    name: lineResume["name"],
                    basic_name: lineResume["basic_name"],
                    display_name: lineResume["display_name"],
                    isCombo: Boolean(lineResume["isCombo"]),
                    combo_parent_uuid: lineResume["combo_parent_uuid"],
                    note: lineResume["note"],
                    customer_note: lineResume["customer_note"],
                    attribute_value_names: lineResume["attribute_value_names"],
                    group: lineResume["group"],
                    quantity: -quantity,
                };
                changeAbsCount += Math.abs(quantity);
                changesCount += quantity;
            } else {
                changes[lineKey]["quantity"] -= quantity;
            }
        }
    }

    const result = {
        nbrOfChanges: changeAbsCount,
        noteUpdate: noteUpdate,
        orderlines: changes,
        count: changesCount,
    };

    // if `generalCustomerNote` key is present, then there is a change in the generalCustomerNote
    const lastGeneralCustomerNote = order.last_order_preparation_change.general_customer_note || "";
    if (lastGeneralCustomerNote !== order.general_customer_note) {
        result.general_customer_note = order.general_customer_note;
    }
    const lastInternalNote = order.last_order_preparation_change.internal_note || "";
    if (lastInternalNote !== order.internal_note) {
        result.internal_note = order.internal_note;
    }
    return result;
};

export const receiptLineGrouper = {
    getGroup(orderLine) {
        // To be overridden
    },
};
