/* @odoo-module */

import { AttachmentList } from "@mail/core/common/attachment_list";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { Composer } from "@mail/core/common/composer";
import { useDropzone } from "@mail/core/common/dropzone_hook";
import { Thread } from "@mail/core/common/thread";
import { useMessageHighlight, useScrollPosition } from "@mail/utils/common/hooks";
import { isDragSourceExternalFile } from "@mail/utils/common/misc";

import {
    Component,
    onMounted,
    onPatched,
    onWillUpdateProps,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { Dropdown } from "@web/core/dropdown/dropdown";
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
    };
    static props = [
        "close?",
        "compactHeight?",
        "displayName?",
        "hasMessageList?",
        "isChatterAside?",
        "hasParentReloadOnAttachmentsChanged?",
        "hasParentReloadOnMessagePosted?",
        "isAttachmentBoxVisibleInitially?",
        "isInFormSheetBg?",
        "threadId?",
        "threadModel",
        "webRecord?",
        "saveRecord?",
        "hasComposer?",
        "twoColumns?",
    ];
    static defaultProps = {
        compactHeight: false,
        hasMessageList: true,
        isChatterAside: false,
        hasParentReloadOnAttachmentsChanged: false,
        hasParentReloadOnMessagePosted: false,
        isAttachmentBoxVisibleInitially: false,
        isInFormSheetBg: true,
        threadId: false,
        hasComposer: true,
        twoColumns: false,
    };
    /** @type {number|null} */
    loadingAttachmentTimeout = null;

    setup() {
        this.action = useService("action");
        this.attachmentBox = useRef("attachment-box");
        this.threadService = useService("mail.thread");
        this.store = useState(useService("mail.store"));
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.state = useState({
            composerType: false,
            isAttachmentBoxOpened: this.props.isAttachmentBoxVisibleInitially,
            jumpThreadPresent: 0,
            scrollToAttachments: 0,
            showAttachmentLoading: false,
            /** @type {import("models").Thread} */
            thread: undefined,
        });
        this.attachmentUploader = useAttachmentUploader(
            this.threadService.getThread(this.props.threadModel, this.props.threadId)
        );
        this.scrollPosition = useScrollPosition("root", undefined, "top");
        this.rootRef = useRef("root");
        this.onScrollDebounced = useThrottleForAnimation(this.onScroll);
        this.messageHighlight = useMessageHighlight();
        useChildSubEnv({
            ...this.env,
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
                    if (!this.props.threadId) {
                        const saved = await this.props.saveRecord?.();
                        if (!saved) {
                            return;
                        }
                    }
                    files.forEach((file) => this.attachmentUploader.uploadFile(file));
                    this.state.isAttachmentBoxOpened = true;
                }
            },
            "o-mail-Chatter-dropzone"
        );

        onMounted(async () => {
            if (this.props.threadId) {
                this.state.thread = this.store.Thread.insert({
                    id: this.props.threadId,
                    model: this.props.threadModel,
                    name: this.props.webRecord?.data?.display_name || undefined,
                });
            }
            if (this.props.hasComposer) {
                await this.load(this.props.threadId, this.requestList);
            }
            this.scrollPosition.restore();
        });
        onPatched(this.scrollPosition.restore);
        onWillUpdateProps((nextProps) => {
            this.willUpdateProps(nextProps);
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
                if (
                    this.state.thread &&
                    !["new", "loading"].includes(this.state.thread.status) &&
                    this.state.scrollToAttachments > 0
                ) {
                    this.attachmentBox.el.scrollIntoView({ block: "center" });
                }
            },
            () => [this.state.thread?.status, this.state.scrollToAttachments]
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
                }
                return () => browser.clearTimeout(this.loadingAttachmentTimeout);
            },
            () => [this.state.thread, this.state.thread?.isLoadingAttachments]
        );
    }

    get requestList() {
        return [];
    }

    /**
     * @returns {boolean}
     */
    get isDisabled() {
        return !this.props.threadId || !this.state.thread?.hasReadAccess;
    }

    get attachments() {
        return this.state.thread?.attachments ?? [];
    }

    willUpdateProps(nextProps) {
        this.load(nextProps.threadId, this.requestList);
        if (nextProps.threadId === false) {
            this.state.composerType = false;
        }
        this.attachmentUploader.thread = this.threadService.getThread(
            nextProps.threadModel,
            nextProps.threadId
        );
        if (this.onNextUpdate) {
            if (!this.onNextUpdate(nextProps)) {
                this.onNextUpdate = null;
            }
        }
    }

    /**
     * @param {number} threadId
     * @param {['attachments'|'messages']} requestList
     */
    load(threadId = this.props.threadId, requestList = ["attachments", "messages"]) {
        const { threadModel } = this.props;
        this.state.thread = this.threadService.getThread(threadModel, threadId);
        this.scrollPosition.model = this.state.thread?.scrollPosition;
        if (!threadId) {
            return;
        }
        this.threadService.fetchData(this.state.thread, requestList);
    }

    onPostCallback() {
        if (this.props.hasParentReloadOnMessagePosted) {
            this.reloadParentView();
        }
        this.toggleComposer();
        this.state.jumpThreadPresent++;
        // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
        const requestList = this.requestList;
        requestList.splice(this.requestList.indexOf("attachments"), 1, "messages");
        this.load(this.props.threadId, requestList);
    }

    async reloadParentView() {
        await this.props.saveRecord?.();
        if (this.props.webRecord) {
            await this.props.webRecord.load();
        }
    }

    toggleComposer(mode = false) {
        const toggle = () => {
            if (this.state.composerType === mode) {
                this.state.composerType = false;
            } else {
                this.state.composerType = mode;
            }
        };
        if (this.props.threadId) {
            toggle();
        } else {
            this.onNextUpdate = (nextProps) => {
                // @returns {boolean} retry on next update
                // if there is no threadId, the save operation probably failed
                // probably because some required field is not set
                if (nextProps.threadId) {
                    toggle();
                } else {
                    return true;
                }
            };
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
        this.scrollPosition.ref.el.scrollTop = 0;
    }

    onClickAddAttachments() {
        if (this.attachments.length === 0) {
            return;
        }
        this.state.isAttachmentBoxOpened = !this.state.isAttachmentBoxOpened;
        if (this.state.isAttachmentBoxOpened) {
            this.state.scrollToAttachments++;
        }
    }

    async onClickAttachFile(ev) {
        if (this.props.threadId) {
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
