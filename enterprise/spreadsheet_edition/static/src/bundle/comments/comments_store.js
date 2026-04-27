import { helpers, stores } from "@odoo/o-spreadsheet";
const { positionToZone, isInside } = helpers;

const { SpreadsheetStore, CellPopoverStore } = stores;

const ACTIVE_BACKGROUND_COLOR = "#FFD73333";

export class CommentsStore extends SpreadsheetStore {
    mutators = ["toggleComments", "openCommentThread"];
    selectedThreadId = undefined;
    /** @private */
    areCommentsActive = true;
    cellPopoverStore = this.get(CellPopoverStore);
    drawResolvedBackground = false;

    constructor(get) {
        super(get);
        this.model.selection.observe(this, {
            handleEvent: this.handleEvent.bind(this),
        });
    }

    handle(cmd) {
        switch (cmd.type) {
            case "SET_VIEWPORT_OFFSET":
                if (this.cellPopoverStore.persistentCellPopover?.type === "OdooCellComment") {
                    this.cellPopoverStore.close();
                }
                break;
        }
    }

    get renderingLayers() {
        return ["Triangle"];
    }

    handleEvent(event) {
        if (this.getters.isGridSelectionActive() && !this.getters.isReadonly()) {
            this.drawResolvedBackground = false;
            const position = this.getters.getActivePosition();
            const threads = this.getters.getCellThreads(position);
            if (threads && threads.length) {
                const thread =
                    threads.find((thread) => thread.threadId === this.selectedThreadId) ||
                    threads.at(-1);
                this.selectedThreadId = thread.threadId;
                if (!thread.isResolved) {
                    this.cellPopoverStore.open(position, "OdooCellComment");
                    this.drawResolvedBackground = true;
                } else {
                    if (this.cellPopoverStore.persistentCellPopover?.type === "OdooCellComment") {
                        this.cellPopoverStore.close();
                    }
                }
            } else {
                this.selectedThreadId = undefined;
            }
        }
    }

    toggleComments() {
        this.areCommentsActive = !this.areCommentsActive;
        if (
            !this.areCommentsActive &&
            this.cellPopoverStore.persistentCellPopover?.type === "OdooCellComment"
        ) {
            this.cellPopoverStore.close();
            this.selectedThreadId = undefined;
        }
    }

    openCommentThread(threadId) {
        const threadInfo = this.getters.getThreadInfo(threadId);
        if (!threadInfo || this.getters.isReadonly()) {
            return;
        }
        this.areCommentsActive = true;
        const { sheetId, col, row } = threadInfo;
        const activeSheetId = this.getters.getActiveSheetId();
        if (sheetId !== activeSheetId) {
            this.model.dispatch("ACTIVATE_SHEET", {
                sheetIdFrom: activeSheetId,
                sheetIdTo: sheetId,
            });
        }
        this.selectedThreadId = threadId;
        this.model.selection.selectCell(col, row);
        this.drawResolvedBackground = true;
    }

    /**
     *
     * @param {*} ctx Grid rendering context
     */
    drawLayer({ ctx }, layer) {
        if (!this.areCommentsActive || layer !== "Triangle" || this.getters.isReadonly()) {
            return;
        }

        const sheetId = this.getters.getActiveSheetId();
        const threadInfos = this.getters.getThreadInfosInSheet(sheetId);

        for (const { col, row, isResolved } of threadInfos) {
            const zone = this.getters.expandZone(sheetId, positionToZone({ col, row }));
            if (zone.left !== col || zone.top !== row) {
                continue;
            }
            const { x, y, width, height } = this.getters.getVisibleRect(zone);
            if (width > 0 && height > 0) {
                const { col: activeCol, row: activeRow } = this.getters.getActivePosition();
                if (
                    isInside(activeCol, activeRow, zone) &&
                    (this.drawResolvedBackground || !isResolved)
                ) {
                    ctx.fillStyle = ACTIVE_BACKGROUND_COLOR;
                    ctx.fillRect(x, y, width, height);
                }
                if (!isResolved) {
                    ctx.fillStyle = "orange";
                    ctx.beginPath();
                    ctx.moveTo(x + 5, y);
                    ctx.lineTo(x, y + 5);
                    ctx.lineTo(x, y);
                    ctx.fill();
                }
            }
        }
    }
}
