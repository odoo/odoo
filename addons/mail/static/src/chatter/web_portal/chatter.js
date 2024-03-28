import { AttachmentList } from "@mail/core/common/attachment_list";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { useMessageHighlight } from "@mail/utils/common/hooks";
import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";

import {
    Component,
    onMounted,
    onWillUpdateProps,
    useChildSubEnv,
    useRef,
    useState,
} from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { FileUploader } from "@web/views/fields/file_handler";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class Chatter extends Component {
    static template = "mail.Chatter";
    static components = {
        AttachmentList,
        Dropdown,
        Thread,
        Composer,
        FileUploader,
        SearchMessagesPanel,
    };
    static props = ["threadId?", "threadModel", "webRecord?", "saveRecord?"];
    static defaultProps = { threadId: false };

    setup() {
        this.action = useService("action");
        this.attachmentBox = useRef("attachment-box");
        this.threadService = useService("mail.thread");
        this.store = useState(useService("mail.store"));
        this.orm = useService("orm");
        this.messageService = useService("mail.message");
        this.state = useState({
            composerType: false,
            jumpThreadPresent: 0,
            /** @type {import("models").Thread} */
            thread: undefined,
            isSearchOpen: false,
        });
        this.attachmentUploader = useAttachmentUploader(
            this.store.Thread.insert({ model: this.props.threadModel, id: this.props.threadId })
        );
        this.rootRef = useRef("root");
        this.onScrollDebounced = useThrottleForAnimation(this.onScroll);
        this.messageHighlight = useMessageHighlight();
        useChildSubEnv({
            inChatter: true,
            messageHighlight: this.messageHighlight,
        });

        onMounted(() => {
            this.changeThread(this.props.threadModel, this.props.threadId, this.props.webRecord);
            if (!this.env.chatter || this.env.chatter?.fetchData) {
                if (this.env.chatter) {
                    this.env.chatter.fetchData = false;
                }
                this.load(this.state.thread, this.requestList);
            }
        });
        onWillUpdateProps((nextProps) => {
            if (
                this.props.threadId !== nextProps.threadId ||
                this.props.threadModel !== nextProps.threadModel
            ) {
                this.changeThread(nextProps.threadModel, nextProps.threadId, nextProps.webRecord);
            }
            if (!this.env.chatter || this.env.chatter?.fetchData) {
                if (this.env.chatter) {
                    this.env.chatter.fetchData = false;
                }
                this.load(this.state.thread, this.requestList);
            }
        });
    }

    get afterPostRequestList() {
        return ["messages"];
    }

    get requestList() {
        return [];
    }

    changeThread(threadModel, threadId, webRecord) {
        this.state.thread = this.store.Thread.insert({ model: threadModel, id: threadId });
        this.state.thread.name = webRecord?.data?.display_name || undefined;
        this.attachmentUploader.thread = this.state.thread;
        if (threadId === false) {
            if (this.state.thread.messages.length === 0) {
                this.state.thread.messages.push({
                    id: this.messageService.getNextTemporaryId(),
                    author: this.store.self,
                    body: _t("Creating a new record..."),
                    message_type: "notification",
                    trackingValues: [],
                    res_id: threadId,
                    model: threadModel,
                });
            }
            this.state.composerType = false;
        } else {
            this.onThreadCreated?.(this.state.thread);
            this.onThreadCreated = null;
            this.closeSearch();
        }
    }

    /**
     * Fetch data for the thread according to the request list.
     * @param {import("models").Thread} thread
     * @param {string[]} requestList
     */
    load(thread, requestList) {
        if (!thread.id || !this.state.thread?.eq(thread)) {
            return;
        }
        this.threadService.fetchData(thread, requestList);
    }

    onPostCallback() {
        this.state.jumpThreadPresent++;
        // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
        this.load(this.state.thread, this.afterPostRequestList);
    }

    async unlinkAttachment(attachment) {
        await this.attachmentUploader.unlink(attachment);
    }

    onClickSearch() {
        this.state.composerType = false;
        this.state.isSearchOpen = !this.state.isSearchOpen;
    }

    closeSearch() {
        this.state.isSearchOpen = false;
    }

    async onClickAttachFile(ev) {
        if (this.state.thread.id) {
            return;
        }
        const saved = await this.props.saveRecord?.();
        if (!saved) {
            return false;
        }
    }

    onScroll() {
        this.state.isTopStickyPinned = this.rootRef.el.scrollTop !== 0;
    }
}
