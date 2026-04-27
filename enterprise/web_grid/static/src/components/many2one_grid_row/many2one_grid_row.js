/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { GridRow, gridRow } from "../grid_row/grid_row";

export class Many2OneGridRow extends GridRow {
    static template = "web_grid.Many2OneGridRow";
    static props = {
        ...GridRow.props,
        relation: { type: String, optional: true },
        canOpen: { type: Boolean, optional: true },
    }
    static defaultProps = {
        ...GridRow.defaultProps,
        canOpen: true,
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    get relation() {
        return this.props.relation || this.props.model.fieldsInfo[this.props.name].relation;
    }

    get urlRelation() {
        if (!this.relation.includes(".")) {
            return "m-" + this.relation;
        }
        return this.relation;
    }

    get displayName() {
        return this.value && this.value[1].split("\n", 1)[0];
    }

    get extraLines() {
        return this.value
            ? this.value[1]
                  .split("\n")
                  .map((line) => line.trim())
                  .slice(1)
            : [];
    }

    get resId() {
        return this.value && this.value[0];
    }

    async openAction() {
        const action = await this.orm.call(this.relation, "get_formview_action", [[this.resId]], {
            context: this.props.context,
        });
        await this.actionService.doAction(action);
    }

    onClick(ev) {
        if (this.props.canOpen) {
            ev.stopPropagation();
            this.openAction();
        }
    }
}

export const many2OneGridRow = {
    ...gridRow,
    component: Many2OneGridRow,
};

registry.category("grid_components").add("many2one", many2OneGridRow);
