/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { renderToString } from "@web/core/utils/render";
import { useSortable } from "@web/core/utils/sortable_owl";
import { standardViewProps } from "@web/views/standard_view_props";
import { BoardAction } from "./board_action";
import { blockDom, Component, useState, useRef } from "@odoo/owl";

export class BoardController extends Component {
    setup() {
        this.board = useState(this.props.board);
        this.rpc = useService("rpc");
        this.dialogService = useService("dialog");
        if (this.env.isSmall) {
            this.selectLayout("1", false);
        } else {
            const mainRef = useRef("main");
            useSortable({
                ref: mainRef,
                elements: ".o-dashboard-action",
                handle: ".o-dashboard-action-header",
                cursor: "move",
                groups: ".o-dashboard-column",
                connectGroups: true,
                onDrop: ({ element, previous, parent }) => {
                    const fromColIdx = parseInt(element.parentElement.dataset.idx, 10);
                    const fromActionIdx = parseInt(element.dataset.idx, 10);
                    const toColIdx = parseInt(parent.dataset.idx, 10);
                    const toActionIdx = previous ? parseInt(previous.dataset.idx, 10) + 1 : 0;
                    if (fromColIdx !== toColIdx) {
                        // to reduce visual flickering
                        element.classList.add("d-none");
                    }
                    this.moveAction(fromColIdx, fromActionIdx, toColIdx, toActionIdx);
                },
            });
        }
    }

    moveAction(fromColIdx, fromActionIdx, toColIdx, toActionIdx) {
        const action = this.board.columns[fromColIdx].actions[fromActionIdx];
        if (fromColIdx !== toColIdx) {
            // action moving from a column to another
            this.board.columns[fromColIdx].actions.splice(fromActionIdx, 1);
            this.board.columns[toColIdx].actions.splice(toActionIdx, 0, action);
        } else {
            // move inside a column
            if (fromActionIdx === toActionIdx) {
                return;
            }
            const actions = this.board.columns[fromColIdx].actions;
            if (fromActionIdx < toActionIdx) {
                actions.splice(toActionIdx + 1, 0, action);
                actions.splice(fromActionIdx, 1);
            } else {
                actions.splice(fromActionIdx, 1);
                actions.splice(toActionIdx, 0, action);
            }
        }
        this.saveBoard();
    }

    selectLayout(layout, save = true) {
        const currentColNbr = this.board.colNumber;
        const nextColNbr = layout.split("-").length;
        if (nextColNbr < currentColNbr) {
            // need to move all actions in last cols in the last visible col
            const cols = this.board.columns;
            const lastVisibleCol = cols[nextColNbr - 1];
            for (let i = nextColNbr; i < currentColNbr; i++) {
                lastVisibleCol.actions.push(...cols[i].actions);
                cols[i].actions = [];
            }
        }
        this.board.layout = layout;
        this.board.colNumber = nextColNbr;
        if (save) {
            this.saveBoard();
        }
        if (document.querySelector("canvas")) {
            // horrible hack to force charts to be recreated so they pick up the
            // proper size. also, no idea why raf is needed :(
            browser.requestAnimationFrame(() => this.render(true));
        }
    }

    closeAction(column, action) {
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Are you sure that you want to remove this item?"),
            confirm: () => {
                const index = column.actions.indexOf(action);
                column.actions.splice(index, 1);
                this.saveBoard();
            },
            cancel: () => {},
        });
    }

    toggleAction(action, save = true) {
        action.isFolded = !action.isFolded;
        if (save) {
            this.saveBoard();
        }
    }

    saveBoard() {
        const templateFn = renderToString.app.getTemplate("board.arch");
        const bdom = templateFn(this.board, {});
        const root = document.createElement("rendertostring");
        blockDom.mount(bdom, root);
        const result = xmlSerializer.serializeToString(root);
        const arch = result.slice(result.indexOf("<", 1), result.indexOf("</rendertostring>"));

        this.rpc("/web/view/edit_custom", {
            custom_id: this.board.customViewId,
            arch,
        });
        this.env.bus.trigger("CLEAR-CACHES");
    }
}

BoardController.template = "board.BoardView";
BoardController.components = { BoardAction, Dropdown, DropdownItem };
BoardController.props = {
    ...standardViewProps,
    board: Object,
};

const xmlSerializer = new XMLSerializer();
