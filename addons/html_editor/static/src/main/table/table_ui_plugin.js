import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { TableMenu } from "./table_menu";
import { TablePicker } from "./table_picker";
import { registry } from "@web/core/registry";

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

        this.columnMenuOverlayKey = "table-column-menu";
        this.rowMenuOverlayKey = "table-row-menu";
        this.activeTd = null;

        this.addDomListener(this.document, "pointermove", this.onMouseMove);
        const closeMenus = () => {
            if (this.isMenuOpened) {
                this.isMenuOpened = false;
                this.closeColumnMenu();
                this.closeRowMenu();
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
        const targetCell = closestElement(target, "td, th");
        if (targetCell && targetCell !== this.activeTd && this.editable.contains(targetCell)) {
            if (ev.target.isContentEditable) {
                this.setActiveTd(targetCell);
            }
        } else if (this.activeTd) {
            const isOverlay = target.closest(".o-we-table-menu");
            if (isOverlay) {
                return;
            }
            if (!targetCell) {
                this.setActiveTd(null);
            }
        }
    }

    createDropdownState(closeMenu) {
        const dropdownState = reactive({
            isOpen: false,
            open: () => {
                dropdownState.isOpen = true;
                closeMenu();
                this.isMenuOpened = true;
            },
            close: () => {
                dropdownState.isOpen = false;
                this.isMenuOpened = false;
            },
        });
        return dropdownState;
    }

    closeColumnMenu() {
        registry.category(this.config.localOverlayContainers.key).remove(this.columnMenuOverlayKey);
    }

    closeRowMenu() {
        registry.category(this.config.localOverlayContainers.key).remove(this.rowMenuOverlayKey);
    }

    setActiveTd(td) {
        this.activeTd = td;
        this.closeColumnMenu();
        this.closeRowMenu();
        if (!td) {
            return;
        }
        const withAddStep = (fn) => {
            return (...args) => {
                fn(...args);
                this.dependencies.history.addStep();
            };
        };
        const tableMethods = {
            moveColumn: withAddStep(this.dependencies.table.moveColumn),
            addColumn: withAddStep(this.dependencies.table.addColumn),
            removeColumn: withAddStep(this.dependencies.table.removeColumn),
            moveRow: withAddStep(this.dependencies.table.moveRow),
            addRow: withAddStep(this.dependencies.table.addRow),
            removeRow: withAddStep(this.dependencies.table.removeRow),
            resetTableSize: withAddStep(this.dependencies.table.resetTableSize),
        };
        if (td.cellIndex === 0) {
            registry.category(this.config.localOverlayContainers.key).add(this.rowMenuOverlayKey, {
                Component: TableMenu,
                props: {
                    type: "row",
                    target: td,
                    dropdownState: this.createDropdownState(this.closeColumnMenu.bind(this)),
                    direction: this.config.direction || "ltr",
                    close: () => this.closeRowMenu(),
                    ...tableMethods,
                },
            });
        }
        if (td.parentElement.rowIndex === 0) {
            registry
                .category(this.config.localOverlayContainers.key)
                .add(this.columnMenuOverlayKey, {
                    Component: TableMenu,
                    props: {
                        type: "column",
                        target: td,
                        dropdownState: this.createDropdownState(this.closeRowMenu.bind(this)),
                        direction: this.config.direction || "ltr",
                        close: () => this.closeColumnMenu(),
                        ...tableMethods,
                    },
                });
        }
    }
}
