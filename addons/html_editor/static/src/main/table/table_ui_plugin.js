import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { TableMenu } from "./table_menu";
import { TablePicker } from "./table_picker";

/**
 * This plugin only contains the table ui feature (table picker, menus, ...).
 * All actual table manipulation code is located in the table plugin.
 */
export class TableUIPlugin extends Plugin {
    static name = "table_ui";
    static dependencies = ["overlay", "table"];
    /** @type { (p: TableUIPlugin) => Record<string, any> } */
    static resources = (p) => ({
        powerboxCommands: [
            {
                name: _t("Table"),
                description: _t("Insert a table"),
                category: "structure",
                fontawesome: "fa-table",
                action(dispatch) {
                    if (p.services.ui.isSmall) {
                        dispatch("INSERT_TABLE", { cols: 3, rows: 3 });
                    } else {
                        dispatch("OPEN_TABLE_PICKER");
                    }
                },
            },
        ],
    });

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.picker = this.shared.createOverlay(TablePicker, {
            position: "bottom-start",
            onPositioned: (picker, position) => {
                const popperRect = picker.getBoundingClientRect();
                const { left } = position;
                if (this.config.direction === "rtl") {
                    // position from the right instead of the left as it is needed
                    // to ensure the expand animation is properly done
                    if (left < 0) {
                        picker.style.right = `${-popperRect.width - left}px`;
                    } else {
                        picker.style.right = `${window.innerWidth - left - popperRect.width}px`;
                    }
                    picker.style.removeProperty("left");
                }
            },
        });

        this.activeTd = null;

        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.colMenu = this.shared.createOverlay(TableMenu, {
            position: "top-fit",
            offsetY: 0,
            sequence: 30,
        });
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.rowMenu = this.shared.createOverlay(TableMenu, {
            position: "left-fit",
            sequence: 30,
        });
        this.addDomListener(this.document, "pointermove", this.onMouseMove);
        this.addDomListener(this.document, "click", () => {
            if (this.isMenuOpened) {
                this.isMenuOpened = false;
                this.colMenu.close();
                this.rowMenu.close();
            }
        });
    }

    handleCommand(command) {
        switch (command) {
            case "OPEN_TABLE_PICKER":
                this.openPicker();
                break;
        }
    }

    openPicker() {
        const range = this.document.getSelection().getRangeAt(0);
        const rect = range.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0 && rect.x === 0) {
            range.startContainer.parentElement.appendChild(this.document.createElement("br"));
        }
        this.picker.open({
            props: {
                dispatch: this.dispatch,
                editable: this.editable,
                overlay: this.picker,
                direction: this.config.direction,
            },
        });
    }

    onMouseMove(ev) {
        const target = ev.target;
        if (this.isMenuOpened) {
            return;
        }
        if (
            ev.target.tagName === "TD" &&
            target !== this.activeTd &&
            this.editable.contains(target)
        ) {
            if (ev.target.isContentEditable) {
                this.setActiveTd(target);
            }
        } else if (this.activeTd) {
            const isOverlay = target.closest(".o-overlay-container");
            if (isOverlay) {
                return;
            }
            const parentTd = closestElement(target, "td");
            if (!parentTd) {
                this.setActiveTd(null);
            }
        }
    }

    createDropdownState(menuToClose) {
        const dropdownState = reactive({
            isOpen: false,
            open: () => {
                dropdownState.isOpen = true;
                menuToClose.close();
                this.isMenuOpened = true;
            },
            close: () => {
                dropdownState.isOpen = false;
                this.isMenuOpened = false;
            },
        });
        return dropdownState;
    }

    setActiveTd(td) {
        this.activeTd = td;
        this.colMenu.close();
        this.rowMenu.close();
        if (!td) {
            return;
        }
        if (td.cellIndex === 0) {
            this.rowMenu.open({
                target: td,
                props: {
                    type: "row",
                    dispatch: this.dispatch,
                    overlay: this.rowMenu,
                    target: td,
                    dropdownState: this.createDropdownState(this.colMenu),
                },
            });
        }
        if (td.parentElement.rowIndex === 0) {
            this.colMenu.open({
                target: td,
                props: {
                    type: "column",
                    dispatch: this.dispatch,
                    overlay: this.colMenu,
                    target: td,
                    dropdownState: this.createDropdownState(this.rowMenu),
                    direction: this.config.direction,
                },
            });
        }
    }
}
