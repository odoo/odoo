import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { QuickVoiceSettings } from "@mail/discuss/call/common/quick_voice_settings";
import { patch } from "@web/core/utils/patch";

patch(QuickVoiceSettings.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
    },
    onClickVoiceSettings() {
        this.actionService.doAction({
            context: {
                dialog_size: "medium",
                footer: false,
            },
            name: _t("Voice & Video Settings"),
            tag: "mail.discuss_call_settings_action",
            target: "new",
            type: "ir.actions.client",
        });
    },
});
