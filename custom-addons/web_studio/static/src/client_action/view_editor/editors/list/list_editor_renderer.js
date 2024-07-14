/** @odoo-module */
import { listView } from "@web/views/list/list_view";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { reactive, useEffect, useState } from "@odoo/owl";
import { AddButtonAction } from "../../interactive_editor/action_button/action_button";

const colSelectedClass = "o-web-studio-editor--element-clicked";
const colHoverClass = "o-web-studio--col-hovered";

function cleanStyling(mainEl, classNames) {
    mainEl.querySelectorAll(`${classNames.map((c) => `.${c}`)}`).forEach((el) => {
        el.classList.remove(...classNames);
    });
}

export function columnsStyling(mainEl, colSelector, classNames) {
    mainEl.querySelectorAll(`td${colSelector}, th${colSelector}`).forEach((el) => {
        el.classList.add(...classNames);
    });
}

function getSelectableCol(target, colSelector) {
    if (target.closest("button")) {
        return null;
    }
    const colEl = target.closest(`td${colSelector}, th${colSelector}`);
    return colEl;
}

export class ListEditorRenderer extends listView.Renderer {
    setup() {
        const viewEditorModel = useState(this.env.viewEditorModel);
        this.viewEditorModel = reactive(viewEditorModel, () => {
            // Little trick to update our columns when showInvisible changes on the viewEditorModel
            // getActiveColumns reads that value
            this.state.columns = this.getActiveColumns(this.props.list);
        });
        super.setup();
        this.onTableHover = useThrottleForAnimation(this.onTableHover);

        useEffect(
            (rootEl) => {
                rootEl.classList.add("o_web_studio_list_view_editor");
            },
            () => [this.rootRef.el]
        );
    }

    get canResequenceRows() {
        return false;
    }

    getColumnClass(col) {
        let cls = super.getColumnClass(col);
        if (col.studioColumnInvisible) {
            cls += " o_web_studio_show_invisible";
        }
        return cls;
    }

    getCellClass(col, record) {
        let cls = super.getCellClass(col, record);
        if (col.studioColumnInvisible || super.evalInvisible(col.invisible, record)) {
            cls += " o_web_studio_show_invisible";
        }
        return cls;
    }

    getColumnHookData(col, position) {
        let xpath;
        if (!col) {
            return { xpath: "/tree", position: "inside" };
        }
        if (col.type === "button_group") {
            if (position === "before") {
                xpath = col.buttons[0].studioXpath;
            } else {
                xpath = col.buttons[col.buttons.length - 1].studioXpath;
            }
        } else {
            xpath = col.studioXpath;
        }
        return {
            xpath,
            position,
        };
    }

    addColsHooks(_cols) {
        const attrs = { width: "1px" };
        const options = {};
        const cols = [];
        let hookId = 0;
        const firstCol = _cols.find((c) => c.optional !== "hide");
        const { xpath, position } = this.getColumnHookData(firstCol, "before");
        cols.push({
            type: "studio_hook",
            position,
            xpath,
            id: `studio_hook_${hookId++}_${(firstCol && firstCol.id) || 0}`,
            attrs,
            options,
        });
        for (const col of _cols) {
            if (col.optional === "hide") {
                continue;
            }
            cols.push(col);
            const { xpath, position } = this.getColumnHookData(col, "after");
            cols.push({
                type: "studio_hook",
                position,
                xpath,
                id: `studio_hook_${hookId++}_${col.id}`,
                attrs,
                options,
            });
        }
        return cols;
    }

    get allColumns() {
        let cols = this._allColumns;
        if (this.viewEditorModel.showInvisible) {
            cols = cols.map((c) => {
                return {
                    ...c,
                    optional: false,
                    studioColumnInvisible:
                        c.optional === "hide" || this.props.evalViewModifier(c.column_invisible),
                };
            });
        } else {
            cols = cols.filter((c) => !this.evalColumnInvisible(c.column_invisible));
        }
        return this.addColsHooks(cols);
    }

    set allColumns(cols) {
        this._allColumns = cols;
    }

    evalInvisible(modifier, record) {
        if (this.viewEditorModel.showInvisible) {
            return false;
        }
        return super.evalInvisible(modifier, record);
    }
    evalColumnInvisible(columnInvisible) {
        if (this.viewEditorModel.showInvisible) {
            return false;
        }
        return super.evalColumnInvisible(columnInvisible);
    }

    onTableHover(ev) {
        const table = this.tableRef.el;
        cleanStyling(table, [colHoverClass]);
        if (ev.type !== "mouseover") {
            return;
        }
        const colEl = getSelectableCol(ev.target, "[data-studio-xpath]");
        if (!colEl) {
            return;
        }
        const xpath = colEl.dataset.studioXpath;
        columnsStyling(table, `[data-studio-xpath='${xpath}']:not(.o_web_studio_hook)`, [
            colHoverClass,
        ]);
    }

    onTableClicked(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const table = ev.currentTarget;
        cleanStyling(table, [colSelectedClass]);
        const colEl = getSelectableCol(ev.target, "[data-studio-xpath]");
        if (!colEl) {
            return;
        }
        this.env.config.onNodeClicked(colEl.dataset.studioXpath);
    }

    makeTooltipButton(button) {
        return JSON.stringify({
            button: {
                string: button.string,
                type: button.clickParams?.type,
                name: button.clickParams?.name,
            },
            debug: true,
        });
    }
}
ListEditorRenderer.template = "web_studio.ListEditorRenderer";
ListEditorRenderer.recordRowTemplate = "web_studio.ListEditorRenderer.RecordRow";
ListEditorRenderer.components = {
    ...listView.Renderer.components,
    AddButtonAction,
};
