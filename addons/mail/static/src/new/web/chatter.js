/* @odoo-module */

import { Thread } from "../core_ui/thread";
import { useMessaging, useStore } from "../core/messaging_hook";
import { useDropzone } from "@mail/new/dropzone/dropzone_hook";
import { AttachmentList } from "@mail/new/attachments/attachment_list";
import { Composer } from "../composer/composer";
import { Activity } from "@mail/new/activity/activity";
import {
    Component,
    markup,
    onMounted,
    onPatched,
    onWillStart,
    onWillUpdateProps,
    useChildSubEnv,
    useRef,
    useState,
} from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { isDragSourceExternalFile } from "@mail/new/utils/misc";
import { removeFromArrayWithPredicate } from "@mail/new/utils/arrays";
import { useAttachmentUploader } from "@mail/new/attachments/attachment_uploader_hook";
import { useHover, useScrollPosition } from "@mail/new/utils/hooks";
import { FollowerSubtypeDialog } from "./follower_subtype_dialog";
import { _t } from "@web/core/l10n/translation";
import { SuggestedRecipientsList } from "../composer/suggested_recipient_list";

/**
 * @typedef {Object} Props
 * @property {function} [close]
 * @extends {Component<Props, Env>}
 */
export class Chatter extends Component {
    static components = {
        AttachmentList,
        Dropdown,
        Thread,
        Composer,
        Activity,
        FileUploader,
        SuggestedRecipientsList,
    };
    static defaultProps = {
        compactHeight: false,
        hasActivity: true,
        resId: false,
        hasFollowers: true,
    };
    static props = [
        "close?",
        "compactHeight?",
        "hasActivity?",
        "hasFollowers?",
        "resId?",
        "resModel",
        "displayName?",
        "isAttachmentBoxOpenedInitially?",
        "webRecord?",
    ];
    static template = "mail.chatter";

    /** @type {import("@mail/new/core/messaging_service").Messaging} */
    messaging;
    /** @type {import("@mail/new/core/thread_model").Thread} */
    thread;

    setup() {
        this.action = useService("action");
        this.messaging = useMessaging();
        this.activity = useState(useService("mail.activity"));
        this.attachment = useService("mail.attachment");
        /** @type {import("@mail/new/web/chatter_service").ChatterService} */
        this.chatter = useState(useService("mail.chatter"));
        this.threadService = useService("mail.thread");
        /** @type {import('@mail/new/core/persona_service').PersonaService} */
        this.personaService = useService("mail.persona");
        this.store = useStore();
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.state = useState({
            attachments: [],
            showActivities: true,
            isAttachmentBoxOpened: this.props.isAttachmentBoxOpenedInitially,
            isLoadingAttachments: false,
        });
        this.unfollowHover = useHover("unfollow");
        this.attachmentUploader = useAttachmentUploader(
            this.chatter.getThread(this.props.resModel, this.props.resId)
        );
        this.scrollPosition = useScrollPosition("scrollable", undefined, "top");
        this.rootRef = useRef("root");
        useChildSubEnv({
            inChatter: true,
        });
        useDropzone(this.rootRef, (ev) => {
            if (this.thread.composer.type) {
                return;
            }
            if (isDragSourceExternalFile(ev.dataTransfer)) {
                [...ev.dataTransfer.files].forEach(this.attachmentUploader.uploadFile);
                this.state.isAttachmentBoxOpened = true;
            }
        });

        onMounted(this.scrollPosition.restore);
        onPatched(this.scrollPosition.restore);
        onWillStart(() =>
            this.load(this.props.resId, ["followers", "attachments", "suggestedRecipients"])
        );
        onWillUpdateProps((nextProps) => {
            if (nextProps.resId !== this.props.resId) {
                this.state.isLoadingAttachments = false;
                this.load(nextProps.resId, ["followers", "attachments", "suggestedRecipients"]);
                if (nextProps.resId === false) {
                    this.thread.composer.type = false;
                }
            }
        });
    }

    /**
     * @returns {import("@mail/new/activity/activity_model").Activity[]}
     */
    get activities() {
        return Object.values(this.store.activities).filter((activity) => {
            return (
                activity.res_model === this.props.resModel && activity.res_id === this.props.resId
            );
        });
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
        return !this.props.resId || !this.thread.hasReadAccess;
    }

    get attachments() {
        return this.attachmentUploader.attachments.concat(this.state.attachments);
    }

    /**
     * @param {number} resId
     * @param {['activities'|'followers'|'attachments'|'messages'|'suggestedRecipients']} requestList
     */
    load(
        resId = this.props.resId,
        requestList = ["followers", "attachments", "messages", "suggestedRecipients"]
    ) {
        const { resModel } = this.props;
        const thread = this.chatter.getThread(resModel, resId);
        this.thread = thread;
        this.scrollPosition.model = this.thread.scrollPosition;
        if (!resId) {
            // todo: reset activities/attachments/followers
            return;
        }
        this.state.isLoadingAttachments = requestList.includes("attachments");
        if (this.props.hasActivity && !requestList.includes("activities")) {
            requestList.push("activities");
        }
        this.chatter.fetchData(resId, resModel, requestList).then((result) => {
            this.thread.hasReadAccess = result.hasReadAccess;
            this.thread.hasWriteAccess = result.hasWriteAccess;
            if ("activities" in result) {
                const existingIds = new Set();
                for (const activity of result.activities) {
                    if (activity.note) {
                        activity.note = markup(activity.note);
                    }
                    existingIds.add(this.activity.insert(activity).id);
                }
                for (const activity of this.activities) {
                    if (!existingIds.has(activity.id)) {
                        this.activity.delete(activity);
                    }
                }
            }
            if ("attachments" in result) {
                this.state.attachments = result.attachments.map((attachment) =>
                    this.attachment.insert(attachment)
                );
                this.state.isLoadingAttachments = false;
            }
            if ("followers" in result) {
                for (const followerData of result.followers) {
                    this.chatter.insertFollower({
                        followedThread: this.thread,
                        ...followerData,
                    });
                }
            }
            if ("suggestedRecipients" in result) {
                this.chatter.insertSuggestedRecipients(this.thread, result.suggestedRecipients);
            }
        });
    }

    onClickAddFollowers() {
        document.body.click(); // hack to close dropdown
        const action = {
            type: "ir.actions.act_window",
            res_model: "mail.wizard.invite",
            view_mode: "form",
            views: [[false, "form"]],
            name: _t("Invite Follower"),
            target: "new",
            context: {
                default_res_model: this.props.resModel,
                default_res_id: this.props.resId,
            },
        };
        this.env.services.action.doAction(action, {
            onClose: () => this.onFollowerChanged(),
        });
    }

    onClickDetails(ev, follower) {
        this.messaging.openDocument({ id: follower.partner.id, model: "res.partner" });
        document.body.click(); // hack to close dropdown
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("@mail/new/core/follower_model").Follower} follower
     */
    async onClickEdit(ev, follower) {
        this.env.services.dialog.add(FollowerSubtypeDialog, {
            follower,
            onFollowerChanged: () => this.onFollowerChanged(),
        });
        document.body.click(); // hack to close dropdown
    }

    async onClickFollow() {
        await this.orm.call(this.props.resModel, "message_subscribe", [[this.props.resId]], {
            partner_ids: [this.store.self.id],
        });
        this.onFollowerChanged();
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("@mail/new/core/follower_model").Follower} follower
     */
    async onClickRemove(ev, follower) {
        await this.chatter.removeFollower(follower);
        this.onFollowerChanged();
        document.body.click(); // hack to close dropdown
    }

    async onClickUnfollow() {
        await this.chatter.removeFollower(this.thread.followerOfSelf);
        this.onFollowerChanged();
    }

    onFollowerChanged() {
        // TODO condition to reload parent view (message_follower_ids / hasParentReloadOnFollowersUpdate)
        this.reloadParentView();
        this.load(this.props.resId, ["followers", "suggestedRecipients"]);
    }

    async reloadParentView() {
        if (this.props.webRecord) {
            await this.props.webRecord.model.root.load(
                { resId: this.props.resId },
                { keepChanges: true }
            );
            this.props.webRecord.model.notify();
        }
    }

    toggleComposer(mode = false) {
        if (this.thread.composer.type === mode) {
            this.thread.composer.type = false;
        } else {
            this.thread.composer.type = mode;
        }
    }

    toggleActivities() {
        this.state.showActivities = !this.state.showActivities;
    }

    async scheduleActivity() {
        await this.activity.schedule(this.props.resModel, this.props.resId);
        this.load(this.props.resId, ["activities"]);
    }

    get unfollowText() {
        return _t("Unfollow");
    }

    async unlinkAttachment(attachment) {
        await this.attachmentUploader.unlink(attachment);
        removeFromArrayWithPredicate(this.state.attachments, ({ id }) => attachment.id === id);
    }

    onUploaded(data) {
        this.attachmentUploader.uploadData(data);
        this.state.isAttachmentBoxOpened = true;
    }

    onClickAddAttachments() {
        if (this.attachments.length === 0) {
            return;
        }
        this.state.isAttachmentBoxOpened = !this.state.isAttachmentBoxOpened;
    }
}
