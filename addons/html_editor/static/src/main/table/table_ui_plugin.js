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
    static id = "tableUi";
    static dependencies = ["history", "overlay", "table"];
    resources = {
        user_commands: [
            {
                id: "openTablePicker",
                title: _t("Table"),
                description: _t("Insert a table"),
                icon: "fa-table",
                run: this.openPickerOrInsertTable.bind(this),
            },
        ],
        powerbox_items: [
            {
                categoryId: "structure",
                commandId: "openTablePicker",
            },
        ],
        power_buttons: { commandId: "openTablePicker" },
    };

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.picker = this.dependencies.overlay.createOverlay(TablePicker, {
            positionOptions: {
                updatePositionOnResize: false,
                onPositioned: (picker, position) => {
                    const popperRect = picker.getBoundingClientRect();
                    const { left } = position;
                    if (this.config.direction === "rtl") {
                        // position from the right instead of the left as it is needed
                        // to ensure the expand animation is properly done
                        picker.style.right = `${window.innerWidth - left - popperRect.width}px`;
                        picker.style.removeProperty("left");
                    }
                },
            },
        });

        this.activeTd = null;

        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.colMenu = this.dependencies.overlay.createOverlay(TableMenu, {
            positionOptions: {
                position: "top-fit",
                flip: false,
            },
        });
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.rowMenu = this.dependencies.overlay.createOverlay(TableMenu, {
            positionOptions: {
                position: "left-fit",
            },
        });
        this.addDomListener(this.document, "pointermove", this.onMouseMove);
        const closeMenus = () => {
            if (this.isMenuOpened) {
                this.isMenuOpened = false;
                this.colMenu.close();
                this.rowMenu.close();
            }
        };
        this.addDomListener(this.document, "scroll", closeMenus, true);
    }

    openPicker() {
        this.picker.open({
            props: {
                editable: this.editable,
                overlay: this.picker,
                direction: this.config.direction || "ltr",
                insertTable: (params) => this.dependencies.table.insertTable(params),
            },
        });
    }

    openPickerOrInsertTable() {
        if (this.services.ui.isSmall) {
            this.dependencies.table.insertTable({ cols: 3, rows: 3 });
        } else {
            this.openPicker();
        }
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
        const withAddStep =
            (fn) =>
            (...args) => {
                fn(...args);
                this.dependencies.history.addStep();
            };
        const tableMethods = {
            moveColumn: withAddStep(this.dependencies.table.moveColumn),
            addColumn: withAddStep(this.dependencies.table.addColumn),
            removeColumn: withAddStep(this.dependencies.table.removeColumn),
            moveRow: withAddStep(this.dependencies.table.moveRow),
            addRow: withAddStep(this.dependencies.table.addRow),
            removeRow: withAddStep(this.dependencies.table.removeRow),
            resetTableSize: withAddStep(this.dependencies.table.resetTableSize),
            clearColumnContent: withAddStep(this.dependencies.table.clearColumnContent),
            clearRowContent: withAddStep(this.dependencies.table.clearRowContent),
        };
        if (td.cellIndex === 0) {
            this.rowMenu.open({
                target: td,
                props: {
                    type: "row",
                    overlay: this.rowMenu,
                    target: td,
                    dropdownState: this.createDropdownState(this.colMenu),
                    ...tableMethods,
                },
            });
        }
        if (td.parentElement.rowIndex === 0) {
            this.colMenu.open({
                target: td,
                props: {
                    type: "column",
                    overlay: this.colMenu,
                    target: td,
                    dropdownState: this.createDropdownState(this.rowMenu),
                    direction: this.config.direction || "ltr",
                    ...tableMethods,
                },
            });
        }
    }
}
