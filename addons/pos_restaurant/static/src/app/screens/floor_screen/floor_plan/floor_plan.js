import { FloorPlanBase } from "@pos_restaurant/app/screens/floor_screen/floor_plan_base";
import { markRaw, onWillUnmount, useEffect, useExternalListener } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { setElementTransform } from "@pos_restaurant/app/services/floor_plan/utils/utils";
import { calculateBoundsFromTransform } from "@pos_restaurant/app/services/floor_plan/utils/bounds_calculator";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

const TABLE_LINKING_DELAY = 400;

export class FloorPlan extends FloorPlanBase {
    static template = "pos_restaurant.floor_plan";
    static components = {};
    static props = {};

    setup() {
        super.setup();
        this.pos = usePos();
        this.alert = useService("alert");
        this.ui = useService("ui");
        useExternalListener(window, "resize", useDebounced(this.handleWindowResize, 100));
        this.scrollFloorId = null;
        useEffect(
            (selectedFloor, isKanban) => {
                this.onFloorChange(selectedFloor, isKanban);
            },
            () => [this.floorPlanStore.selectedFloor, this.floorPlanStore.isKanban()]
        );
        this.initTableLinkDND();
        onWillUnmount(() => {
            this.saveScrollPosition();
        });
    }

    onFloorChange(selectedFloor, isKanban) {
        if (isKanban) {
            return;
        }

        // Save scroll position  (must be done before ensureBoardFits)
        this.saveScrollPosition();
        this.ensureBoardFits();

        selectedFloor?.ensureBgImageLoaded().then((hasChanged) => {
            if (hasChanged) {
                this.ensureBoardFits();
            }
        });

        if (selectedFloor) {
            // Restore scroll position
            this.scrollFloorId = selectedFloor.id; // Track the previous floor when this method is called again (to save its position)
            const scrollPosition = this.floorPlanStore.getFloorScrollPositions(selectedFloor.id);
            if (scrollPosition) {
                this.containerRef.el?.scrollTo(scrollPosition);
            } else {
                // Scroll to first visible table
                const firstTable = selectedFloor.getFirstVisibleTable();
                if (firstTable) {
                    this.scrollToElement(firstTable.uuid, "auto");
                }
            }
        }
    }

    saveScrollPosition() {
        if (!this.scrollFloorId || !this.containerRef.el) {
            return;
        }
        const scrollContainerEl = this.containerRef.el;
        this.floorPlanStore.storeFloorScrollPosition(this.scrollFloorId, {
            left: scrollContainerEl.scrollLeft,
            top: scrollContainerEl.scrollTop,
        });
    }

    getChangeCount(tableId) {
        return this.pos.getChangeCount(tableId);
    }

    get isKanban() {
        return this.floorPlanStore.isKanban();
    }

    getTablesSortedByNumber() {
        return this.selectedFloor?.getTablesSortedByNumber() || [];
    }

    getFloorDecorElements() {
        return markRaw(this.floorPlanStore.getFloorDecorElements() || []);
    }

    handleWindowResize() {
        this.ensureBoardFits();
    }

    ensureBoardFits() {
        if (!this.selectedFloor || this.isKanban) {
            return;
        }
        const size = this.selectedFloor.getSize();

        let canvasWidth = size.width;
        let canvasHeight = size.height;

        const scrollContainer = this.containerRef.el;

        // Add some padding if overflow
        if (canvasWidth > scrollContainer.clientWidth) {
            canvasWidth += 20;
        } else {
            canvasWidth = 0; //100% width
        }
        if (canvasHeight > scrollContainer.clientHeight) {
            canvasHeight += 20;
        } else {
            canvasHeight = 0; //100% height
        }

        this.state.canvasWidth = canvasWidth;
        this.state.canvasHeight = canvasHeight;
        // Assign the size and style here to be able to scroll correctly
        this.canvasRef.el.style = this.getCanvasStyles();
    }

    getContainerStyle() {
        if (this.isKanban) {
            return "";
        }

        return this.selectedFloor?.getContainerStyle() || "";
    }

    async onClickTable(table, ev) {
        if (table.parent_id) {
            return this.onClickTable(table.parent_id, ev);
        }
        if (!this.pos.isOrderTransferMode) {
            await this.pos.setTableFromUi(table);
        }
    }

    mergeOrder(table, parentTable, parentSide, element) {
        const tableMO = table.record;
        const currentTableMOParent = tableMO.parent_id;
        const newTableMOParent = parentTable?.record;
        if (!currentTableMOParent && !newTableMOParent) {
            // Was not linked and is not linked
            return false;
        }

        if (
            currentTableMOParent === newTableMOParent &&
            parentSide === currentTableMOParent.parent_side
        ) {
            // Same link
            return false;
        }

        if (!newTableMOParent) {
            const mainOrder = this.pos.getActiveOrdersOnTable(tableMO.rootTable)?.[0];
            this.pos.restoreOrdersToOriginalTable(mainOrder, tableMO);
        } else if (currentTableMOParent !== newTableMOParent) {
            const oToTrans = this.pos.getActiveOrdersOnTable(tableMO)[0];
            if (oToTrans) {
                this.pos.mergeTableOrders(oToTrans.uuid, newTableMOParent);
            }
        }

        this.pos.data.write("restaurant.table", [tableMO.id], {
            parent_id: newTableMOParent ? newTableMOParent.id : null,
            parent_side: newTableMOParent ? parentSide : null,
        });
        return parentTable;
    }

    animateElementTransition(element) {
        element.classList.add("o_fp_animate_transition");
        const onEnd = () => {
            element.classList.remove("o_fp_animate_transition");
            element.removeEventListener("transitionend", onEnd);
        };
        element.addEventListener("transitionend", onEnd);
    }

    initTableLinkDND() {
        let dndContext = null;
        const suggestLinkingPositions = () =>
            dndContext.targetTable && dndContext.time + TABLE_LINKING_DELAY < Date.now();

        const findIntersectingTableElem = (draggedLeft, draggedTop) => {
            const { table, tableGeo } = dndContext;
            const draggedBounds = calculateBoundsFromTransform({
                ...tableGeo,
                left: draggedLeft,
                top: draggedTop,
            });

            const tables = this.floorPlanStore.getFloorTables();
            for (const otherTable of tables) {
                if (otherTable === table || otherTable.hasParent()) {
                    //Ignore same table or  already linked tables
                    continue;
                }
                const bounds = otherTable.getBounds();
                if (
                    draggedBounds.left < bounds.right &&
                    draggedBounds.right > bounds.left &&
                    draggedBounds.top < bounds.bottom &&
                    draggedBounds.bottom > bounds.top
                ) {
                    return otherTable;
                }
            }
            return null;
        };

        const restoreToOriginalPosition = (element, table) => {
            this.animateElementTransition(element);
            const { left, top } = table.linkedPosition;
            setElementTransform(element, left, top, table.rotation, table.scale);
        };

        const snapToParent = (element, table, targetTable, canvasRect, x, y) => {
            const parentBounds = targetTable.getBounds();
            const canvasX = x - canvasRect.left;
            const canvasY = y - canvasRect.top;
            const dx = canvasX - (parentBounds.left + parentBounds.width / 2);
            const dy = canvasY - (parentBounds.top + parentBounds.height / 2);

            const side =
                Math.abs(dx) > Math.abs(dy)
                    ? dx > 0
                        ? "right"
                        : "left"
                    : dy > 0
                    ? "bottom"
                    : "top";

            const snapPos = table.computeLinkedPosition(targetTable, side);
            dndContext.targetSide = side;
            setElementTransform(element, snapPos.left, snapPos.top, table.rotation, table.scale);
        };
        const clearCtxTarget = () => {
            if (dndContext.targetElement) {
                dndContext.targetElement.classList.remove("link_target");
            }
            dndContext.targetElement = null;
            dndContext.targetTable = null;
            dndContext.targetSide = null;
            dndContext.time = null;
        };

        useDraggable({
            ref: this.canvasRef,
            elements: ".table",
            enabled: true,
            onDragStart: ({ addClass, element }) => {},

            onWillStartDrag: ({ addClass, element, x, y }) => {
                addClass(element, "shadow");
                addClass(this.canvasRef.el, "o_fp_table_linking");

                dndContext = {};
                const uuid = this.getTableUuidFromDOMEl(element);
                const table = this.floorPlanStore.getElementByUuid(uuid);
                dndContext.table = table;
                dndContext.tableGeo = table.getGeometry();

                // Calculate offset from cursor to table's logical position
                const canvasRect = this.canvasRef.el.getBoundingClientRect();
                const tablePos = table.linkedPosition;
                dndContext.dragOffset = {
                    x: x - canvasRect.left - tablePos.left,
                    y: y - canvasRect.top - tablePos.top,
                };
            },

            onDrag: ({ element, x, y, addClass }) => {
                const { table, dragOffset, targetTable } = dndContext;
                const canvasRect = this.canvasRef.el.getBoundingClientRect();
                const newLeft = x - canvasRect.left - dragOffset.x;
                const newTop = y - canvasRect.top - dragOffset.y;

                clearTimeout(dndContext.checkTimeout);
                dndContext.checkTimeout = null;

                const potentialParentTable = findIntersectingTableElem(newLeft, newTop);
                if (potentialParentTable !== targetTable) {
                    clearCtxTarget();
                }

                if (!suggestLinkingPositions()) {
                    setElementTransform(element, newLeft, newTop, table.rotation, table.scale);

                    if (!potentialParentTable) {
                        this.alert.add("Link Table");
                        return;
                    }

                    if (potentialParentTable === targetTable) {
                        //Still over the same target, schedule a check in case the user doesn't move the cursor
                        dndContext.checkTimeout = setTimeout(() => {
                            dndContext.checkTimeout = null;
                            snapToParent(element, table, targetTable, canvasRect, x, y);
                        }, Math.max(1, TABLE_LINKING_DELAY - (Date.now() - dndContext.time)));
                        return;
                    }

                    const targetElement = this.getDOMFloorElement(potentialParentTable.uuid);
                    addClass(targetElement, "link_target");
                    dndContext.targetElement = targetElement;
                    dndContext.targetTable = potentialParentTable;
                    dndContext.time = Date.now();
                    this.alert.add(
                        `Link Table ${table.table_number} with ${potentialParentTable.table_number}`
                    );
                    return;
                }

                snapToParent(element, table, targetTable, canvasRect, x, y);
            },
            onDrop: ({ element }) => {
                let { targetTable, table, targetSide } = dndContext;
                const hasTarget = targetTable && targetSide; // maybe waiting for delay
                if (!hasTarget) {
                    targetTable = null;
                    targetSide = null;
                }

                dndContext.isMerged = this.mergeOrder(table, targetTable, targetSide, element);
            },

            onDragEnd: ({ element }) => {
                const { isMerged, table } = dndContext;
                if (!isMerged) {
                    restoreToOriginalPosition(element, table);
                }
                clearTimeout(dndContext.checkTimeout);
                this.alert.dismiss();
                dndContext = null;
            },
        });
    }
}

const useDraggable = makeDraggableHook({
    name: "useDraggable",

    onComputeParams({ ctx }) {
        ctx.followCursor = false;
        ctx.delay = 300;
    },

    onWillStartDrag: ({ ctx }) => ({ element: ctx.current.element }),
    onDragStart: ({ ctx }) => ({ element: ctx.current.element }),
    onDrag: ({ ctx }) => ({ element: ctx.current.element }),
    onDrop: ({ ctx }) => ({ element: ctx.current.element }),
    onDragEnd: ({ ctx }) => ({ element: ctx.current.element }),
});
