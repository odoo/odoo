import { reactive } from "@web/owl2/utils";
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { _t } from "@web/core/l10n/translation";
import { MobileTablePicker } from "./mobile_table_picker";
import { TableMenu } from "./table_menu";
import { TablePicker } from "./table_picker";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { TableDragDrop } from "./table_drag_drop";
import { registry } from "@web/core/registry";
import { getRowIndex } from "@html_editor/utils/table";

/**
 * This plugin only contains the table ui feature (table picker, menus, ...).
 * All actual table manipulation code is located in the table plugin.
 */
export class TableUIPlugin extends Plugin {
    static id = "tableUi";
    static dependencies = ["history", "overlay", "selection", "table"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "openTablePicker",
                title: _t("Table"),
                description: _t("Insert a table"),
                icon: "fa-table",
                run: this.openPickerOrInsertTable.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_items: [
            {
                categoryId: "structure",
                commandId: "openTablePicker",
            },
        ],
        selectionchange_handlers: this.updateActiveCell.bind(this),
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

        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.mobilePicker = this.dependencies.overlay.createOverlay(MobileTablePicker, {
            positionOptions: {
                updatePositionOnResize: false,
                onPositioned: (picker) => {
                    picker.style.bottom = 0;
                    picker.style.width = "100%";
                    picker.style.removeProperty("top");
                },
            },
        });

        this.activeTd = null;
        this.columnMenuOverlayKey = "table-column-menu";
        this.rowMenuOverlayKey = "table-row-menu";

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
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.tableDragDropOverlay = this.dependencies.overlay.createOverlay(TableDragDrop);
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

    openMobilePicker() {
        this.mobilePicker.open({
            props: {
                editable: this.editable,
                close: () => {
                    this.mobilePicker.close();
                    this.dependencies.selection.focusEditable();
                },
                insertTable: (params) => this.dependencies.table.insertTable(params),
            },
        });
    }

    openPickerOrInsertTable() {
        if (this.services.ui.isSmall) {
            this.openMobilePicker();
        } else {
            this.openPicker();
        }
    }

    updateActiveCell(selectionData) {
        const selection = selectionData.editableSelection;
        const selectedTd = closestElement(selection.startContainer, ".o_selected_td");
        if (selection.isCollapsed || !selectedTd) {
            return;
        }
        this.activeTd = false;
    }

    onMouseMove(ev) {
        const target = ev.target;
        if (this.isMenuOpened) {
            return;
        }
        const targetCell = closestElement(target, "td, th");
        if (targetCell && targetCell !== this.activeTd && this.editable.contains(targetCell)) {
            if (ev.target.isContentEditable && closestElement(target, "table").isContentEditable) {
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
            turnIntoHeader: withAddStep(this.dependencies.table.turnIntoHeader),
            turnIntoRow: withAddStep(this.dependencies.table.turnIntoRow),
            resetRowHeight: withAddStep(this.dependencies.table.resetRowHeight),
            resetColumnWidth: withAddStep(this.dependencies.table.resetColumnWidth),
            resetTableSize: withAddStep(this.dependencies.table.resetTableSize),
            clearColumnContent: withAddStep(this.dependencies.table.clearColumnContent),
            clearRowContent: withAddStep(this.dependencies.table.clearRowContent),
            toggleAlternatingRows: withAddStep(this.dependencies.table.toggleAlternatingRows),
            mergeSelectedCells: withAddStep(this.dependencies.table.mergeSelectedCells),
            unmergeSelectedCell: withAddStep(this.dependencies.table.unmergeSelectedCell),
            buildTableGrid: this.dependencies.table.buildTableGrid,
        };
        const grid = this.dependencies.table.buildTableGrid(closestElement(td, "table"));
        const rowIndex = getRowIndex(td.parentElement);
        if (grid[rowIndex][0] === td) {
            registry.category(this.config.localOverlayContainers.key).add(this.rowMenuOverlayKey, {
                Component: TableMenu,
                props: {
                    type: "row",
                    tableDragDropOverlay: this.tableDragDropOverlay,
                    target: td,
                    dropdownState: this.createDropdownState(this.closeColumnMenu.bind(this)),
                    direction: this.config.direction || "ltr",
                    close: () => this.closeRowMenu(),
                    document: this.document,
                    editable: this.editable,
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
                        tableDragDropOverlay: this.tableDragDropOverlay,
                        dropdownState: this.createDropdownState(this.closeRowMenu.bind(this)),
                        direction: this.config.direction || "ltr",
                        document: this.document,
                        editable: this.editable,
                        close: () => this.closeColumnMenu(),
                        ...tableMethods,
                    },
                });
        }
    }
}
