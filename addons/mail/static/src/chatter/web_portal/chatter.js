import { AttachmentList } from "@mail/core/common/attachment_list";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { Composer } from "@mail/core/common/composer";
import { useDropzone } from "@mail/core/common/dropzone_hook";
import { Thread } from "@mail/core/common/thread";
import { useMessageHighlight } from "@mail/utils/common/hooks";
import { isDragSourceExternalFile } from "@mail/utils/common/misc";
import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";

import {
    Component,
    onMounted,
    onWillUpdateProps,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useThrottleForAnimation } from "@web/core/utils/timing";
import { FileUploader } from "@web/views/fields/file_handler";

export const DELAY_FOR_SPINNER = 1000;

/**
 * @typedef {Object} Props
 * @property {function} [close]
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
    static props = [
        "close?",
        "compactHeight?",
        "displayName?",
        "isChatterAside?",
        "hasParentReloadOnAttachmentsChanged?",
        "hasParentReloadOnMessagePosted?",
        "isAttachmentBoxVisibleInitially?",
        "isInFormSheetBg?",
        "threadId?",
        "threadModel",
        "webRecord?",
        "saveRecord?",
    ];
    static defaultProps = {
        compactHeight: false,
        isChatterAside: false,
        hasParentReloadOnAttachmentsChanged: false,
        hasParentReloadOnMessagePosted: false,
        isAttachmentBoxVisibleInitially: false,
        isInFormSheetBg: true,
        threadId: false,
    };
    /** @type {number|null} */
    loadingAttachmentTimeout = null;

    setup() {
        this.action = useService("action");
        this.attachmentBox = useRef("attachment-box");
        this.threadService = useService("mail.thread");
        this.store = useState(useService("mail.store"));
        this.orm = useService("orm");
        this.messageService = useService("mail.message");
        this.state = useState({
            composerType: false,
            isAttachmentBoxOpened: this.props.isAttachmentBoxVisibleInitially,
            jumpThreadPresent: 0,
            showAttachmentLoading: false,
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
        useDropzone(
            this.rootRef,
            async (ev) => {
                if (this.state.composerType) {
                    return;
                }
                if (isDragSourceExternalFile(ev.dataTransfer)) {
                    const files = [...ev.dataTransfer.files];
                    if (!this.state.thread.id) {
                        const saved = await this.props.saveRecord?.();
                        if (!saved) {
                            return;
                        }
                    }
                    Promise.all(files.map((file) => this.attachmentUploader.uploadFile(file))).then(
                        () => {
                            if (this.props.hasParentReloadOnAttachmentsChanged) {
                                this.reloadParentView();
                            }
                        }
                    );
                    this.state.isAttachmentBoxOpened = true;
                }
            },
            "o-mail-Chatter-dropzone"
        );

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
        useEffect(
            () => {
                if (
                    this.state.thread &&
                    !["new", "loading"].includes(this.state.thread.status) &&
                    this.attachments.length === 0
                ) {
                    this.state.isAttachmentBoxOpened = false;
                }
            },
            () => [this.state.thread?.status, this.attachments]
        );
        useEffect(
            () => {
                if (!this.state.thread) {
                    return;
                }
                browser.clearTimeout(this.loadingAttachmentTimeout);
                if (this.state.thread?.isLoadingAttachments) {
                    this.loadingAttachmentTimeout = browser.setTimeout(
                        () => (this.state.showAttachmentLoading = true),
                        DELAY_FOR_SPINNER
                    );
                } else {
                    this.state.showAttachmentLoading = false;
                    this.state.isAttachmentBoxOpened =
                        this.props.isAttachmentBoxVisibleInitially && this.attachments.length > 0;
                }
                return () => browser.clearTimeout(this.loadingAttachmentTimeout);
            },
            () => [this.state.thread, this.state.thread?.isLoadingAttachments]
        );
    }

    get afterPostRequestList() {
        return ["messages"];
    }

    get requestList() {
        return [];
    }

    /**
     * @returns {boolean}
     */
    get isDisabled() {
        return !this.state.thread.id || !this.state.thread?.hasReadAccess;
    }

    get attachments() {
        return this.state.thread?.attachments ?? [];
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
        if (this.props.hasParentReloadOnMessagePosted) {
            this.reloadParentView();
        }
        this.toggleComposer();
        this.state.jumpThreadPresent++;
        // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
        this.load(this.state.thread, this.afterPostRequestList);
    }

    async reloadParentView() {
        await this.props.saveRecord?.();
        if (this.props.webRecord) {
            await this.props.webRecord.load();
        }
    }

    toggleComposer(mode = false) {
        this.closeSearch();
        const toggle = () => {
            if (this.state.composerType === mode) {
                this.state.composerType = false;
            } else {
                this.state.composerType = mode;
            }
        };
        if (this.state.thread.id) {
            toggle();
        } else {
            this.onThreadCreated = toggle;
            this.props.saveRecord?.();
        }
    }

    async unlinkAttachment(attachment) {
        await this.attachmentUploader.unlink(attachment);
        if (this.props.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
    }

    onUploaded(data) {
        this.attachmentUploader.uploadData(data);
        if (this.props.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
        this.state.isAttachmentBoxOpened = true;
        this.rootRef.el.scrollTop = 0;
        this.state.thread.scrollTop = 0;
    }

    onClickAddAttachments() {
        if (this.attachments.length === 0) {
            return;
        }
        this.state.isAttachmentBoxOpened = !this.state.isAttachmentBoxOpened;
        if (this.state.isAttachmentBoxOpened) {
            this.rootRef.el.scrollTop = 0;
            this.state.thread.scrollTop = 0;
        }
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
