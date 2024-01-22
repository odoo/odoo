/** @odoo-module **/

import {Component} from "@odoo/owl";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {registry} from "@web/core/registry";
import {archParseBoolean} from "@web/views/utils";
import {X2Many2DMatrixRenderer} from "@web_widget_x2many_2d_matrix/components/x2many_2d_matrix_renderer/x2many_2d_matrix_renderer.esm";

export class X2Many2DMatrixField extends Component {
    setup() {
        this.activeField = this.props.record.activeFields[this.props.name];
    }

    getList() {
        return this.props.value;
    }

    get list() {
        return this.getList();
    }

    _getDefaultRecordValues() {
        return {};
    }

    async commitChange(x, y, value) {
        const fields = this.props.matrixFields;
        const values = this._getDefaultRecordValues();

        const matchingRecords = this.list.records.filter((record) => {
            let recordX = record.data[fields.x];
            let recordY = record.data[fields.y];
            if (record.fields[fields.x].type === "many2one") {
                recordX = recordX[0];
            }
            if (record.fields[fields.y].type === "many2one") {
                recordY = recordY[0];
            }
            return recordX === x && recordY === y;
        });
        if (matchingRecords.length === 1) {
            values[fields.value] = value;
            await matchingRecords[0].update(values);
        } else {
            values[fields.x] = x;
            values[fields.y] = y;

            if (this.list.fields[this.props.matrixFields.x].type === "many2one") {
                values[fields.x] = [x, "/"];
            }
            if (this.list.fields[this.props.matrixFields.y].type === "many2one") {
                values[fields.y] = [y, "/"];
            }

            let total = 0;
            if (matchingRecords.length) {
                total = matchingRecords
                    .map((r) => r.data[fields.value])
                    .reduce((aggr, v) => aggr + v);
            }
            const diff = value - total;
            values[fields.value] = diff;
            const record = await this.list.addNew({
                mode: "edit",
            });
            await record.update(values);
        }
        this.props.setDirty(false);
    }
}

X2Many2DMatrixField.template = "web_widget_x2many_2d_matrix.X2Many2DMatrixField";
X2Many2DMatrixField.props = {
    ...standardFieldProps,
    matrixFields: Object,
    isXClickable: Boolean,
    isYClickable: Boolean,
    showRowTotals: Boolean,
    showColumnTotals: Boolean,
};
X2Many2DMatrixField.components = {X2Many2DMatrixRenderer};
X2Many2DMatrixField.extractProps = ({attrs}) => {
    return {
        matrixFields: {
            value: attrs.field_value,
            x: attrs.field_x_axis,
            y: attrs.field_y_axis,
        },
        isXClickable: archParseBoolean(attrs.x_axis_clickable),
        isYClickable: archParseBoolean(attrs.y_axis_clickable),
        showRowTotals:
            "show_row_totals" in attrs ? archParseBoolean(attrs.show_row_totals) : true,
        showColumnTotals:
            "show_column_totals" in attrs
                ? archParseBoolean(attrs.show_column_totals)
                : true,
    };
};

registry.category("fields").add("x2many_2d_matrix", X2Many2DMatrixField);
