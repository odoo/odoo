import { x2ManyCommands } from "@web/core/orm_service";
import { _t } from "@web/core/l10n/translation";

import { helpers } from "@odoo/o-spreadsheet";
import { OdooUIPlugin } from "@spreadsheet/plugins";

const { positionToZone } = helpers;

export class FieldSyncUIPlugin extends OdooUIPlugin {
    static getters = ["getFieldSyncX2ManyCommands"];
    static layers = ["Triangle"];

    handle(cmd) {
        switch (cmd.type) {
            case "AUTOFILL_CELL": {
                const sheetId = this.getters.getActiveSheetId();
                const origin = this.getters.getFieldSync({
                    sheetId,
                    col: cmd.originCol,
                    row: cmd.originRow,
                });
                if (origin) {
                    const targetCol = cmd.col;
                    const targetRow = cmd.row;
                    const delta = targetRow - cmd.originRow;
                    this.dispatch("ADD_FIELD_SYNC", {
                        sheetId,
                        col: targetCol,
                        row: targetRow,
                        listId: origin.listId,
                        fieldName: origin.fieldName,
                        indexInList: origin.indexInList + delta,
                    });
                }
                break;
            }
        }
    }

    getFieldSyncMaxPosition() {
        const fieldSyncs = [...this.getters.getAllFieldSyncs().values()];
        return Math.max(...fieldSyncs.map((fieldSync) => fieldSync.indexInList));
    }

    async getFieldSyncX2ManyCommands() {
        const commands = [];
        const errors = [];
        const list = this.getters.getMainSaleOrderLineList();
        const listDataSource = this.getters.getListDataSource(list.id);
        const maxPosition = this.getFieldSyncMaxPosition();
        if (!listDataSource.isReady() || !listDataSource.getIdFromPosition(maxPosition)) {
            listDataSource.increaseMaxPosition(maxPosition + 1);
            await listDataSource.load({ reload: true });
        }
        if (!listDataSource.isValid()) {
            return [];
        }
        const duplicationErrors = this.getDuplicatedFieldSyncs();
        if (duplicationErrors) {
            errors.push(...duplicationErrors);
        }
        const fields = listDataSource.getFields();
        const valuesPerOrderLine = {};
        for (const [position, fieldSync] of this.getters.getAllFieldSyncs()) {
            const { listId, indexInList, fieldName } = fieldSync;
            const { value: orderLineId } = this.getters.getListCellValueAndFormat(
                listId,
                indexInList,
                "id"
            );
            const cell = this.getters.getEvaluatedCell(position);
            if (cell.type === "empty" || cell.value === "") {
                continue;
            }
            const field = fields[fieldName];
            if (orderLineId) {
                const {
                    checkType,
                    error: typeError,
                    castToServerValue,
                } = this.getFieldTypeSpec(field.type);
                if (checkType(cell)) {
                    valuesPerOrderLine[orderLineId] ??= {};
                    valuesPerOrderLine[orderLineId][fieldName] = castToServerValue(cell);
                } else {
                    const range = this.getters.getRangeFromZone(
                        position.sheetId,
                        positionToZone(position)
                    );
                    const error = _t(
                        'The value of %(cell_reference)s (%(cell_value)s) can\'t be used for field "%(field_name)s".',
                        {
                            cell_reference: this.getters.getRangeString(
                                range,
                                this.getters.getActiveSheetId()
                            ),
                            cell_value: cell.formattedValue,
                            field_name: field.string,
                        }
                    );
                    errors.push(error + " " + typeError);
                }
            }
        }
        for (const orderLineOrderId in valuesPerOrderLine) {
            const values = valuesPerOrderLine[orderLineOrderId];
            commands.push(x2ManyCommands.update(Number(orderLineOrderId), values));
        }
        return { commands, errors };
    }

    /**
     * @private
     */
    getDuplicatedFieldSyncs() {
        const errors = [];
        const map = {};
        for (const [position, fieldSync] of this.getters.getAllFieldSyncs()) {
            const { listId, indexInList, fieldName } = fieldSync;
            const key = `${listId}-${indexInList}-${fieldName}`;
            const cell = this.getters.getEvaluatedCell(position);
            if (cell.type !== "empty" && cell.value !== "") {
                map[key] ??= [];
                map[key].push(position);
            }
        }
        for (const key in map) {
            if (map[key].length > 1) {
                const positions = map[key];
                const ranges = positions
                    .map((position) =>
                        this.getters.getRangeFromZone(position.sheetId, positionToZone(position))
                    )
                    .map((range) =>
                        this.getters.getRangeString(range, this.getters.getActiveSheetId())
                    );
                errors.push(
                    _t(
                        "Multiple cells are updating the same field of the same record! Unable to determine which one to choose: %s",
                        ranges.join(", ")
                    )
                );
            }
        }
        return errors.length ? errors : undefined;
    }

    /**
     * @private
     */
    getFieldTypeSpec(fieldType) {
        switch (fieldType) {
            case "float":
            case "monetary":
                return {
                    checkType: (cell) => cell.type === "number",
                    error: _t("It should be a number."),
                    castToServerValue: (cell) => cell.value,
                };
            case "many2one":
                return {
                    checkType: (cell) => cell.type === "number" && Number.isInteger(cell.value),
                    error: _t("It should be an id."),
                    castToServerValue: (cell) => cell.value,
                };
            case "integer":
                return {
                    checkType: (cell) => cell.type === "number" && Number.isInteger(cell.value),
                    error: _t("It should be an integer."),
                    castToServerValue: (cell) => cell.value,
                };
            case "boolean":
                return {
                    checkType: (cell) => cell.type === "boolean",
                    error: _t("It should be a boolean."),
                    castToServerValue: (cell) => cell.value,
                };
            case "char":
            case "text":
                return {
                    checkType: (cell) => true,
                    error: "",
                    castToServerValue: (cell) => cell.formattedValue,
                };
        }
    }

    drawLayer({ ctx }, layer) {
        const activeSheetId = this.getters.getActiveSheetId();
        for (const [{ col, row, sheetId }] of this.getters.getAllFieldSyncs()) {
            if (sheetId !== activeSheetId) {
                continue;
            }
            const zone = this.getters.expandZone(activeSheetId, positionToZone({ col, row }));
            if (zone.left !== col || zone.top !== row) {
                continue;
            }
            const { x, y, width } = this.getters.getVisibleRect(zone);
            ctx.fillStyle = "#6C4E65";
            ctx.beginPath();

            ctx.moveTo(x + width - 5, y);
            ctx.lineTo(x + width, y);
            ctx.lineTo(x + width, y + 5);
            ctx.fill();
        }
    }
}
