import { Component, useState } from "@odoo/owl";
import { CellThread } from "../components/cell_thread";
import { helpers, stores, components } from "@odoo/o-spreadsheet";
import { CommentsStore } from "../comments_store";
import { _t } from "@web/core/l10n/translation";

const { toXC, createActions } = helpers;
const { useStore } = stores;
const { Menu, Section } = components;

export class CommentThreadsSidePanel extends Component {
    static template = "documents_spreadsheet.CommentThreadsSidePanel";
    static props = { onCloseSidePanel: Function };
    static components = { CellThread, Menu, Section };

    setup() {
        this.state = useState({
            mode: "allSheets",
        });
        this.menuState = useState({
            isOpen: false,
            position: null,
            threadId: undefined,
        });
        this.commentsStore = useStore(CommentsStore);
    }

    get sheetIds() {
        return this.state.mode === "allSheets"
            ? this.env.model.getters.getSheetIds()
            : [this.env.model.getters.getActiveSheetId()];
    }

    get selectedThreadId() {
        return this.commentsStore.selectedThreadId;
    }

    get spreadsheetThreads() {
        const sheetIds =
            this.state.mode === "activeSheet"
                ? [this.env.model.getters.getActiveSheetId()]
                : this.env.model.getters.getSheetIds();
        return this.env.model.getters.getSpreadsheetThreads(sheetIds);
    }

    /**
     * @param {number} numberOfComments
     */
    getNumberOfCommentsLabel(numberOfComments) {
        return numberOfComments === 1 ? _t("1 thread") : _t("%s threads", numberOfComments);
    }

    getThreadTitle(threadId) {
        const { col, row } = this.env.model.getters.getThreadInfo(threadId);
        const xc = toXC(col, row);
        return `${xc}`;
    }

    selectThread(threadId) {
        this.commentsStore.openCommentThread(threadId);
    }

    get menuItems() {
        if (!this.menuState.threadId) {
            return [];
        }
        const { sheetId, col, row, isResolved } = this.env.model.getters.getThreadInfo(
            this.menuState.threadId
        );
        return createActions([
            {
                name: isResolved ? _t("Re-open this thread") : _t("Resolve this thread"),
                execute: () => {
                    this.env.model.dispatch("EDIT_COMMENT_THREAD", {
                        sheetId,
                        col,
                        row,
                        threadId: this.menuState.threadId,
                        isResolved: !isResolved,
                    });
                    this.commentsStore.openCommentThread(this.menuState.threadId);
                },
            },
        ]);
    }

    openMenu(ev, threadId) {
        this.selectThread(threadId);
        const { x, y, height } = ev.target.getBoundingClientRect();
        this.menuState.isOpen = true;
        this.menuState.position = { x, y: y + height };
        this.menuState.threadId = threadId;
    }

    closeMenu() {
        this.menuState.isOpen = false;
        this.menuState.position = null;
        this.menuState.threadId = undefined;
    }
}
