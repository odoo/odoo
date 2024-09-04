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
    resources = {
        powerboxItems: [
            {
                id: "table",
                name: _t("Table"),
                description: _t("Insert a table"),
                category: "structure",
                fontawesome: "fa-table",
                action: (dispatch) => {
                    if (this.services.ui.isSmall) {
                        dispatch("INSERT_TABLE", { cols: 3, rows: 3 });
                    } else {
                        dispatch("OPEN_TABLE_PICKER");
                    }
                },
            },
        ],
        powerButtons: ["table"],
    };

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.picker = this.shared.createOverlay(TablePicker, {
            positionOptions: {
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
            },
        });

        this.activeTd = null;

        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.colMenu = this.shared.createOverlay(TableMenu, {
            positionOptions: {
                position: "top-fit",
                onPositioned: (el, solution) => {
                    // Only accept top position as solution.
                    if (solution.direction !== "top") {
                        el.style.display = "none"; // avoid glitch
                        this.colMenu.close();
                    }
                },
            },
        });
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.rowMenu = this.shared.createOverlay(TableMenu, {
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

    handleCommand(command) {
        switch (command) {
            case "OPEN_TABLE_PICKER":
                this.openPicker();
                break;
        }
    }

    openPicker() {
        this.picker.open({
            props: {
                dispatch: this.dispatch,
                editable: this.editable,
                overlay: this.picker,
                direction: this.config.direction || "ltr",
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
                    direction: this.config.direction || "ltr",
                },
            });
        }
    }
}
