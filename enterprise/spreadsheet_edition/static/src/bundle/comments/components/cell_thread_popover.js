import { Component, useState, onWillUpdateProps, useChildSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Thread } from "@mail/core/common/thread";
import { CellThread } from "./cell_thread";
import { SpreadsheetCommentComposer } from "./spreadsheet_comment_composer";
import { CommentsStore } from "../comments_store";
import { stores } from "@odoo/o-spreadsheet";

const { useStore } = stores;

export class CellThreadPopover extends Component {
    static template = "spreadsheet_edition.CellThreadPopover";
    static components = { Thread, CellThread, SpreadsheetCommentComposer };

    static props = {
        threadId: {
            optional: true,
            type: Number,
        },
        onClosed: {
            optional: true,
            type: Function,
        },
        isInteractive: Boolean,
        position: Object,
    };

    static defaultProps = { focus: false };
    static threadModel = "spreadsheet.cell.thread";

    setup() {
        useChildSubEnv({
            inChatWindow: true,
        });

        /** @type {import("models").Store} */
        this.mailStore = useService("mail.store");
        this.state = useState({
            /** @type {import("models").Thread} */
            thread: undefined,
            isValid: true,
        });
        this.loadThread(this.props.threadId);

        this.commentsStore = useStore(CommentsStore);

        onWillUpdateProps((nextProps) => {
            this.loadThread(nextProps.threadId);
        });
    }

    onFocused() {
        if (this.props.threadId && !this.props.isInteractive) {
            this.commentsStore.openCommentThread(this.props.threadId);
        }
    }

    showAllComments() {
        this.env.openSidePanel("Comments");
    }

    loadThread(threadId) {
        this.state.thread = this.mailStore.Thread.insert({
            model: CellThreadPopover.threadModel,
            id: threadId,
        });
    }

    async insertNewThread(value, postData) {
        if (!value) {
            return;
        }
        const sheetId = this.env.model.getters.getActiveSheetId();
        const threadId = await this.env.insertThreadInSheet({ sheetId, ...this.props.position });
        this.loadThread(threadId);
        await this.state.thread.post(value, postData);
        this.commentsStore.openCommentThread(this.props.threadId);
    }
}
