// @ts-check
/** @odoo-module native */
import { useAttachmentUploader } from "@mail/core/common/attachment_uploader_hook";
import { discussComponentRegistry } from "@mail/core/common/discuss_component_registry";
import { ActivityMailTemplate } from "@mail/core/web/activity_mail_template";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { computeDelay, getMsToTomorrow } from "@mail/utils/common/dates";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { FileUploader } from "@web/core/file_upload";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/ui/popover";

const log = makeLogger("mail.activity");
/**
 * @typedef {Object} Props
 * @property {import("models").Activity} activity
 * @property {function} onActivityChanged
 * @property {function} reloadParentView
 * @extends {Component<Props, import("@web/env").OdooEnv>}
 */
export class Activity extends Component {
    static components = { ActivityMailTemplate, FileUploader };
    static props = ["activity", "onActivityChanged", "reloadParentView"];
    static template = "mail.Activity";

    setup() {
        super.setup();
        this.storeService = useService("mail.store");
        this.linkNavigation = useService("mail.link_navigation");
        this.state = useState({ showDetails: false, day: 0 });
        this.markDonePopover = usePopover(ActivityMarkAsDone, { position: "right" });
        this.avatarCard = usePopover(discussComponentRegistry.get("AvatarCardPopover"));
        onMounted(() => {
            this.updateDelayAtNight();
        });
        onWillUnmount(() => browser.clearTimeout(this.updateDelayMidnightTimeout));
        this.attachmentUploader = useAttachmentUploader(this.thread);
    }

    get displayName() {
        if (this.props.activity.summary) {
            return _t("“%s”", this.props.activity.summary);
        }
        return this.props.activity.display_name;
    }

    updateDelayAtNight() {
        browser.clearTimeout(this.updateDelayMidnightTimeout);
        this.updateDelayMidnightTimeout = browser.setTimeout(() => {
            this.state.day++;
            this.updateDelayAtNight();
        }, getMsToTomorrow() + 100);
    }

    get delay() {
        void this.state.day;
        return computeDelay(this.props.activity.date_deadline);
    }

    toggleDetails() {
        this.state.showDetails = !this.state.showDetails;
    }

    /** @param {MouseEvent} ev */
    async onClickMarkAsDone(ev) {
        if (this.markDonePopover.isOpen) {
            this.markDonePopover.close();
            return;
        }
        this.markDonePopover.open(/** @type {HTMLElement} */ (ev.currentTarget), {
            activity: this.props.activity,
            hasHeader: true,
            onActivityChanged: this.props.onActivityChanged,
        });
    }

    /** @param {{data: string, name: string, type: string}} data */
    async onFileUploaded(data) {
        const thread = this.thread;
        const { id: attachmentId } = await this.attachmentUploader.uploadData(data, {
            activity: this.props.activity,
        });
        log.logic("onFileUploaded marks done", () => ({
            activityId: this.props.activity.id,
            attachmentId,
        }));
        await this.props.activity.markAsDone([attachmentId]);
        this.props.onActivityChanged(thread);
        await thread.fetchNewMessages();
    }

    /** @param {MouseEvent} ev */
    onClickAvatar(ev) {
        if (!this.props.activity.user_id) {
            return;
        }
        const target = ev.currentTarget;
        if (!this.avatarCard.isOpen) {
            this.avatarCard.open(/** @type {HTMLElement} */ (target), {
                id: this.props.activity.user_id.id,
            });
        }
    }

    async edit() {
        const thread = this.thread;
        await this.props.activity.edit();
        this.props.onActivityChanged(thread);
    }

    async unlink() {
        const thread = this.thread;
        const { activity } = this.props;
        log.logic("unlink", () => ({ activityId: activity.id }));
        await this.env.services.orm.unlink("mail.activity", [activity.id]);
        activity.remove();
        this.props.onActivityChanged(thread);
    }

    get thread() {
        return this.env.services["mail.store"].Thread.insert({
            model: this.props.activity.res_model,
            id: this.props.activity.res_id,
        });
    }

    /** @param {MouseEvent} ev */
    async onClick(ev) {
        this.linkNavigation.handleClickOnLink(ev, this.thread);
    }
}
