/**
 * Since changes of move line quantities will not affect the available quantity of the quant before
 * the record has been saved, it is necessary to determine the offset of the DB quant data.
 *
 * @returns {Promise<Map<number, { available_quantity: number }>>} available quantities of the
 *  quants impacted by unsaved move line changes, by quant id
 */
export async function computeDirtyQuantsData(orm, moveId, list, moveLines = list.records) {
    const dirtyQuantsData = new Map();
    const dirtyQuantityMoveLines = moveLines.filter(
        (ml) => !ml.data.quant_id && ml._values.quantity - ml._changes.quantity
    );
    const dirtyQuantMoveLines = moveLines.filter(
        (ml) => ml.data.quant_id.id
    );
    const dirtyMoveLines = [...dirtyQuantityMoveLines, ...dirtyQuantMoveLines];
    const hasDeletedLines = list.resIds.some((id) => !list.currentIds.includes(id));
    if (!dirtyMoveLines.length && !hasDeletedLines) {
        return dirtyQuantsData;
    }
    const match = await orm.call(
        "stock.move.line",
        "get_move_line_quant_match",
        [
            moveLines
                .filter((rec) => rec.resId)
                .map((rec) => rec.resId),
            moveId,
            dirtyMoveLines.filter((rec) => rec.resId).map((rec) => rec.resId),
            dirtyQuantMoveLines.map((ml) => ml.data.quant_id.id),
        ],
        {}
    );
    const quants = match[0];
    if (!quants.length) {
        return dirtyQuantsData;
    }
    const dbMoveLinesData = new Map();
    for (const data of match[1]) {
        dbMoveLinesData.set(data[0], { quantity: data[1].quantity, quantId: data[1].quant_id });
    }
    const offsetByQuant = new Map();
    for (const ml of dirtyQuantMoveLines) {
        const quantId = ml.data.quant_id.id;
        offsetByQuant.set(quantId, (offsetByQuant.get(quantId) || 0) - ml.data.quantity);
        const dbQuantId = dbMoveLinesData.get(ml.resId)?.quantId;
        if (dbQuantId && quantId != dbQuantId) {
            offsetByQuant.set(
                dbQuantId,
                (offsetByQuant.get(dbQuantId) || 0) + dbMoveLinesData.get(ml.resId).quantity
            );
        }
    }
    const offsetByQuantity = new Map();
    for (const ml of dirtyQuantityMoveLines) {
        offsetByQuantity.set(ml.resId, ml._values.quantity - ml._changes.quantity);
    }
    for (const quant of quants) {
        const quantityOffest = quant[1].move_line_ids
            .map((ml) => offsetByQuantity.get(ml) || 0)
            .reduce((val, sum) => val + sum, 0);
        const quantOffest = offsetByQuant.get(quant[0]) || 0;
        dirtyQuantsData.set(quant[0], {
            available_quantity: quant[1].available_quantity + quantityOffest + quantOffest,
        });
    }
    return dirtyQuantsData;
}
