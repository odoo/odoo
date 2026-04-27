import { Component, useState, onWillUpdateProps, useChildSubEnv, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Thread } from "@mail/core/common/thread";
import { Composer } from "@mail/core/common/composer";
import { SpreadsheetCommentComposer } from "./spreadsheet_comment_composer";

export class CellThread extends Component {
    static template = "spreadsheet_edition.CellThread";
    static components = { Thread, Composer, SpreadsheetCommentComposer };

    static props = {
        threadId: Number,
        edit: Boolean,
    };
    static threadModel = "spreadsheet.cell.thread";

    setup() {
        useChildSubEnv({
            inChatWindow: true,
            chatter: {},
        });
        /** @type {import("models").Store} */
        this.mailStore = useService("mail.store");
        this.state = useState({
            /** @type {import("models").Thread} */
            thread: undefined,
        });
        onWillStart(() => this.loadThread(this.props.threadId));

        onWillUpdateProps(async (nextProps) => {
            if (this.props.threadId !== nextProps.threadId) {
                await this.loadThread(nextProps.threadId);
            }
        });
    }

    async loadThread(threadId) {
        this.state.thread = this.mailStore.Thread.insert({
            model: CellThread.threadModel,
            id: threadId,
        });
        await this.state.thread.fetchNewMessages();
    }
}
