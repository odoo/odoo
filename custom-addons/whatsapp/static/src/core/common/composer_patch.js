/** @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { onWillDestroy, useEffect } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.composerDisableCheckTimeout = null;
        useEffect(
            () => {
                clearTimeout(this.composerDisableCheckTimeout);
                this.checkComposerDisabled();
            },
            () => [this.thread?.whatsapp_channel_valid_until]
        );
        onWillDestroy(() => clearTimeout(this.composerDisableCheckTimeout));
    },

    get placeholder() {
        if (
            this.thread &&
            this.thread.type === "whatsapp" &&
            !this.state.active &&
            this.props.composer.threadExpired
        ) {
            return _t(
                "Can't send message as it has been 24 hours since the last message of the User."
            );
        }
        return super.placeholder;
    },

    checkComposerDisabled() {
        if (this.thread && this.thread.type === "whatsapp") {
            const datetime = this.thread.whatsappChannelValidUntilDatetime;
            if (!datetime) {
                return;
            }
            const delta = datetime.ts - Date.now();
            if (delta <= 0) {
                this.state.active = false;
                this.props.composer.threadExpired = true;
            } else {
                this.state.active = true;
                this.props.composer.threadExpired = false;
                this.composerDisableCheckTimeout = setTimeout(() => {
                    this.checkComposerDisabled();
                }, delta);
            }
        }
    },

    /** @override */
    get isSendButtonDisabled() {
        const whatsappInactive = (this.thread && this.thread.type == 'whatsapp' && !this.state.active)
        return super.isSendButtonDisabled || whatsappInactive;
    },

    onDropFile(ev) {
        this.processFileUploading(ev, super.onDropFile.bind(this));
    },

    onPaste(ev) {
        if (ev.clipboardData.files.length === 0) {
            return super.onPaste(ev);
        }
        this.processFileUploading(ev, super.onPaste.bind(this));
    },

    processFileUploading(ev, superCb) {
        if (this.thread?.type === "whatsapp" && this.props.composer.attachments.length > 0) {
            ev.preventDefault();
            this.env.services.notification.add(
                _t("Only one attachment is allowed for each message"),
                { type: "warning" }
            );
            return;
        }
        superCb(ev);
    },
});
