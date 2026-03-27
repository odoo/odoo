import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { QuickVideoSettings } from "../common/quick_video_settings";

patch(QuickVideoSettings.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
    },
    onClickVideoSettings() {
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
