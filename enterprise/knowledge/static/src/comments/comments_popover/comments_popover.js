import { Composer } from "@mail/core/common/composer";
import { KnowledgeCommentCreatorComposer } from "../../mail/composer/composer";
import { KnowledgeThread } from "@knowledge/mail/thread/knowledge_thread";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, useState } from "@odoo/owl";

export class KnowledgeCommentsPopover extends Component {
    static template = "knowledge.KnowledgeCommentsPopover";
    static props = {
        threadId: { type: String },
        close: { type: Function },
    };
    static components = { Composer, KnowledgeThread, KnowledgeCommentCreatorComposer };

    setup() {
        this.commentsService = useService("knowledge.comments");
        this.commentsState = useState(this.commentsService.getCommentsState());
        this.rootRef = useRef("rootRef");
    }

    onPostCallback() {
        this.props.close();
    }

    onCreateThreadCallback(thread) {
        if (thread) {
            this.commentsState.editorThreads[thread.id]?.select();
        }
    }

    get thread() {
        return this.commentsState.threads[this.props.threadId];
    }
}
