/**
 * Checks whether the 2 provided sale order lines are linked.
 *
 * @param linkingSaleOrderLine The line that is linking to the other line.
 * @param linkedSaleOrderLine The line that is linked by the other line.
 * @return {Boolean} Whether the 2 lines are linked.
 */
export function areSaleOrderLinesLinked(linkingSaleOrderLine, linkedSaleOrderLine) {
    const linkingId = linkedSaleOrderLine.isNew
        ? linkingSaleOrderLine.data.linked_virtual_id
        : linkingSaleOrderLine.data.linked_line_id.id;
    const linkedId = linkedSaleOrderLine.isNew
        ? linkedSaleOrderLine.data.virtual_id
        : linkedSaleOrderLine.resId;
    return linkingId && linkingId === linkedId;
}

/**
 * Gets the linked lines of the provided sale order line.
 *
 * @param saleOrderLine The line whose linked lines to get.
 * @return {Object[]} The list of linked lines.
 */
export function getLinkedSaleOrderLines(saleOrderLine) {
    const saleOrder = saleOrderLine.model.root;
    // TODO(loti): this leaves out any combo items that are on another page.
    return saleOrder.data.order_line.records.filter(
        record => areSaleOrderLinesLinked(record, saleOrderLine)
    );
}

/**
 * Serialize a combo item into a format understandable by the server.
 *
 * @param {ProductComboItem} comboItem The combo item to serialize.
 * @return {Object} The serialized combo item.
 */
export function serializeComboItem(comboItem) {
    return {
        combo_item_id: comboItem.id,
        product_id: comboItem.product.id,
        no_variant_attribute_value_ids: comboItem.product.selectedNoVariantPtavIds,
        product_custom_attribute_values: comboItem.product.selectedCustomPtavs.map(
            customPtav => ({
                custom_product_template_attribute_value_id: customPtav.id,
                custom_value: customPtav.value,
            })
        ),
    }
}

/**
 * Get the selected custom PTAV in the provided PTAL, if any.
 *
 * Note: a PTAL can have at most one selected custom PTAV, by design.
 *
 * @param {ProductTemplateAttributeLine.props} ptal The PTAL in which to look for the selected
 *     custom PTAV.
 * @return {Object|undefined} The selected custom PTAV, if any.
 *
 */
export function getSelectedCustomPtav(ptal) {
    const selectedPtavIds = new Set(ptal.selected_attribute_value_ids);
    return ptal.attribute_values.find(ptav => ptav.is_custom && selectedPtavIds.has(ptav.id));
}

/**
 * Return the `no_variant` PTAV ids of the provided sale order line.
 *
 * @param saleOrderLine The sale order line
 * @return {Number[]} The sale order line's `no_variant` PTAV ids.
 */
export function getNoVariantPtavIds(saleOrderLine) {
    return saleOrderLine.product_no_variant_attribute_value_ids.currentIds;
}

/**
 * Return the custom PTAVs of the provided sale order line.
 *
 * @param saleOrderLine The sale order line
 * @return {Promise<CustomPtav[]>} The sale order line's custom PTAVs.
 */
export async function getCustomPtavs(orm, saleOrderLine) {
    // `product.attribute.custom.value` records are not loaded in the view because sub templates
    // are not loaded in list views. Therefore, we fetch them from the server if the record was
    // saved. Otherwise, we use the value stored on the line.
    const customPtavIds = saleOrderLine.product_custom_attribute_value_ids;
    let customPtavs = [];
    if (customPtavIds.records[0]?.isNew) {
        customPtavs = customPtavIds.records.map(record => record.data);
    } else if (customPtavIds.currentIds.length) {
        const specification = {
            custom_product_template_attribute_value_id: {
                fields: { id: {} },
            },
            custom_value: {},
        };
        customPtavs = await orm.webRead(
            'product.attribute.custom.value',
            customPtavIds.currentIds,
            { specification },
        );
    }
    return customPtavs.map(customPtav => ({
        id: customPtav.custom_product_template_attribute_value_id &&
            customPtav.custom_product_template_attribute_value_id.id,
        value: customPtav.custom_value,
    }));
}

/**
 * Clear the selected combo items of the provided combo line, e.g. before deleting it, so that its
 * (soon to be orphaned) combo item lines aren't left referencing it.
 *
 * @param comboLineRecord The combo line to clear.
 */
export async function clearSelectedComboItems(comboLineRecord) {
    await comboLineRecord.update({ selected_combo_items: "[]" });
}

/**
 * Build the selected-combo-items payload for the provided combo line, from its linked lines.
 */
export async function getSelectedComboItems(orm, comboLineRecord, edit) {
    const comboItemLineRecords = getLinkedSaleOrderLines(comboLineRecord)
        .filter(record => !!record.data.combo_item_id);
    return Promise.all(comboItemLineRecords.map(async record => ({
        id: record.data.combo_item_id?.id,
        no_variant_ptav_ids: edit ? getNoVariantPtavIds(record.data) : [],
        custom_ptavs: edit ? await getCustomPtavs(orm, record.data) : [],
    })));
}
