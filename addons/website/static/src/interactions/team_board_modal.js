import { Component, signal, t, useListener, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { addLoadingEffect } from "@web/core/utils/ui";
import { registry } from "@web/core/registry";

export class SendMessageModal extends Component {
    static template = "website.SendMessageModal";
    static components = { Dialog };

    props = useProps({
        close: t.function(),
        imageSrc: t.string(),
        name: t.string(),
        jobPosition: t.string(),
        infos: t.string(),
    });

    setup() {
        this.sending = signal(false);
        this.notification = useService("notification");
        this.contactMethods = registry.category("website.team_board_contact_methods").getEntries();

        this.modalRef = signal.ref();
        useListener(this.modalRef, "click", this.onClickOutside);
        useListener(this.modalRef, "keydown", this.onKeydown);
    }

    onKeydown = (ev) => {
        if (getActiveHotkey(ev) === "escape" && !this.sending()) {
            this.props.close();
        }
    };

    onClickOutside = (ev) => {
        if (ev.target === ev.currentTarget && !this.sending()) {
            this.props.close();
        }
    };

    async sendMessage(ev) {
        if (this.sending()) {
            return;
        }
        this.sending.set(true);
        const restoreButton = addLoadingEffect(ev.currentTarget);

        try {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            this.props.close();
            this.notification.add(_t("Your message has been sent."), { type: "success" });
        } catch {
            this.notification.add(_t("Your message could not be sent."), { type: "danger" });
        } finally {
            restoreButton();
            this.sending.set(false);
        }
    }

    onContactMethodClick(method) {
        return method.onClick({ name: this.props.name, notification: this.notification });
    }
}
