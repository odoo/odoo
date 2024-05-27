/* @odoo-module */

import { AttachmentList } from "@mail/core/common/attachment_list";
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { Composer } from "@mail/core/common/composer";
import { useDropzone } from "@mail/core/common/dropzone_hook";
import { Thread } from "@mail/core/common/thread";
import { Activity } from "@mail/core/web/activity";
import { SuggestedRecipientsList } from "@mail/core/web/suggested_recipient_list";
import { useHover, useMessageHighlight } from "@mail/utils/common/hooks";
import { isDragSourceExternalFile } from "@mail/utils/common/misc";
import { RecipientList } from "./recipient_list";
import { FollowerList } from "./follower_list";
import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";

import {
    Component,
    markup,
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
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
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
        Activity,
        FileUploader,
        FollowerList,
        SuggestedRecipientsList,
        SearchMessagesPanel,
    };
    static props = [
        "close?",
        "compactHeight?",
        "displayName?",
        "hasActivities?",
        "hasFollowers?",
        "hasMessageList?",
        "isChatterAside?",
        "hasParentReloadOnAttachmentsChanged?",
        "hasParentReloadOnFollowersUpdate?",
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
        hasActivities: true,
        hasFollowers: true,
        hasMessageList: true,
        isChatterAside: false,
        hasParentReloadOnAttachmentsChanged: false,
        hasParentReloadOnFollowersUpdate: false,
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
        this.activityService = useState(useService("mail.activity"));
        this.threadService = useService("mail.thread");
        this.store = useState(useService("mail.store"));
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.state = useState({
            composerType: false,
            isAttachmentBoxOpened: this.props.isAttachmentBoxVisibleInitially,
            jumpThreadPresent: 0,
            showActivities: true,
            showAttachmentLoading: false,
            /** @type {import("models").Thread} */
            thread: undefined,
            isSearchOpen: false,
        });
        this.unfollowHover = useHover("unfollow");
        this.attachmentUploader = useAttachmentUploader(
            this.threadService.getThread(this.props.threadModel, this.props.threadId)
        );
        this.rootRef = useRef("root");
        this.onScrollDebounced = useThrottleForAnimation(this.onScroll);
        this.recipientsPopover = usePopover(RecipientList);
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
                    Promise.all(files.map((file) => this.attachmentUploader.uploadFile(file))).then(() => {
                        if (this.props.hasParentReloadOnAttachmentsChanged) {
                            this.reloadParentView();
                        }
                    })
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
                this.load(this.state.thread, ["followers", "attachments", "suggestedRecipients"]);
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
                this.load(this.state.thread, ["followers", "attachments", "suggestedRecipients"]);
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

    /**
     * @returns {import("models").Activity[]}
     */
    get activities() {
        return this.state.thread?.activities ?? [];
    }

    get followerButtonLabel() {
        return _t("Show Followers");
    }

    get followingText() {
        return _t("Following");
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

    /**
     * @returns {string}
     */
    get toRecipientsText() {
        if (this.state.thread?.recipients.length === 0) {
            return _t("No recipient");
        }
        const recipients = [...(this.state.thread?.recipients ?? [])]
            .slice(0, 5)
            .map(({ partner }) => {
                const text = partner.email ? partner.emailWithoutDomain : partner.name;
                return `<span class="text-muted" title="${escape(
                    partner.email || _t("no email address")
                )}">${escape(text)}</span>`;
            });
        const formatter = new Intl.ListFormat(
            this.store.env.services["user"].lang?.replace("_", "-"),
            { type: "unit" }
        );
        if (this.state.thread && this.state.thread.recipients.length > 5) {
            recipients.push("…");
        }
        return markup(formatter.format(recipients));
    }

    changeThread(threadModel, threadId, webRecord) {
        this.state.thread = this.threadService.getThread(threadModel, threadId);
        this.state.thread.name = webRecord?.data?.display_name || undefined;
        this.attachmentUploader.thread = this.state.thread;
        if (threadId === false) {
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
     * @param {['activities'|'followers'|'attachments'|'messages'|'suggestedRecipients']} requestList
     */
    load(thread, requestList = ["followers", "attachments", "messages", "suggestedRecipients"]) {
        if (!thread.id || !this.state.thread?.eq(thread)) {
            return;
        }
        if (this.props.hasActivities && !requestList.includes("activities")) {
            requestList.push("activities");
        }
        this.threadService.fetchData(thread, requestList);
    }

    async _follow(thread) {
        await this.orm.call(thread.model, "message_subscribe", [[thread.id]], {
            partner_ids: [this.store.self.id],
        });
        this.onFollowerChanged(thread);
    }

    async onClickFollow() {
        if (this.state.thread.id) {
            this._follow(this.state.thread);
        } else {
            this.onThreadCreated = this._follow;
            await this.props.saveRecord?.();
        }
    }

    async onClickUnfollow() {
        const thread = this.state.thread;
        await this.threadService.removeFollower(thread.selfFollower);
        this.onFollowerChanged(thread);
    }

    onFollowerChanged(thread) {
        document.body.click(); // hack to close dropdown
        this.reloadParentView();
        this.load(thread, ["followers", "suggestedRecipients"]);
    }

    onPostCallback() {
        if (this.props.hasParentReloadOnMessagePosted) {
            this.reloadParentView();
        }
        this.toggleComposer();
        this.state.jumpThreadPresent++;
        // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
        this.load(this.state.thread, ["followers", "messages", "suggestedRecipients"]);
    }

    onAddFollowers() {
        this.load(this.state.thread, ["followers", "suggestedRecipients"]);
        if (this.props.hasParentReloadOnFollowersUpdate) {
            this.reloadParentView();
        }
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

    toggleActivities() {
        this.state.showActivities = !this.state.showActivities;
    }

    async scheduleActivity() {
        this.closeSearch();
        const schedule = async (thread) => {
            await this.activityService.schedule(thread.model, [thread.id]);
            this.load(thread, ["activities", "messages"]);
        };
        if (this.state.thread.id) {
            schedule(this.state.thread);
        } else {
            this.onThreadCreated = schedule;
            this.props.saveRecord?.();
        }
    }

    get unfollowText() {
        return _t("Unfollow");
    }

    async unlinkAttachment(attachment) {
        await this.attachmentUploader.unlink(attachment);
        if (this.props.hasParentReloadOnAttachmentsChanged) {
            this.reloadParentView();
        }
    }

    async onUploaded(data) {
        await this.attachmentUploader.uploadData(data);
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

    onClickRecipientList(ev) {
        if (this.recipientsPopover.isOpen) {
            return this.recipientsPopover.close();
        }
        this.recipientsPopover.open(ev.target, { thread: this.state.thread });
    }
}
