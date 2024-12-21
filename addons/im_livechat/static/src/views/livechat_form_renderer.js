import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { CountryFlag } from "@mail/core/common/country_flag";
import { ImStatus } from "@mail/core/common/im_status";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { useMessageHighlight } from "@mail/utils/common/hooks";
import { onWillStart, onWillUpdateProps, useChildSubEnv, useRef, useState } from "@odoo/owl";

import { FileUploader } from "@web/views/fields/file_handler";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FormRenderer } from "@web/views/form/form_renderer";

export class LivechatSessionFormRenderer extends FormRenderer {
    static template = "im_livechat.LivechatDiscuss";
    static components = {
        ...FormRenderer.components,
        AutoresizeInput,
        Composer,
        CountryFlag,
        Thread,
        ThreadIcon,
        FileUploader,
        ImStatus,
    };

    setup() {
        super.setup();
        this.state = useState({ activeAction: null });
        this.contentRef = useRef("content");
        this.root = useRef("root");
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
        this.threadActions = useThreadActions();
        this.messageHighlight = useMessageHighlight();
        useChildSubEnv({
            inDiscussApp: false,
            messageHighlight: this.messageHighlight,
        });
        onWillStart(async () => {
            await this.restoreDiscussThread(this.props);
        });
        onWillUpdateProps(async (nextProps) => {
            await this.restoreDiscussThread(nextProps);
        });
    }

    /**
     * Restore the discuss thread according to record id in the props if
     * necessary.
     *
     * @param {Props} props
     */
    async restoreDiscussThread(props) {
        const activeThread = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: props.record.evalContext.id,
        });
        if (activeThread && activeThread.notEq(this.store.discuss.thread)) {
            activeThread.setAsDiscussThread(false);
        }
        this.store.discuss.hasRestoredThread = true;
    }

    get thread() {
        return this.store.discuss.thread;
    }

    async onFileUploaded(file) {
        await this.thread.notifyAvatarToServer(file.data);
        this.notification.add(_t("The avatar has been updated!"), { type: "success" });
    }

    async renameThread(name) {
        await this.thread.rename(name);
    }

    async updateThreadDescription(description) {
        const newDescription = description.trim();
        if (!newDescription && !this.thread.description) {
            return;
        }
        if (newDescription !== this.thread.description) {
            await this.thread.notifyDescriptionToServer(newDescription);
        }
    }

    async renameGuest(name) {
        const newName = name.trim();
        if (this.store.self.name !== newName) {
            await this.store.self.updateGuestName(newName);
        }
    }
}
