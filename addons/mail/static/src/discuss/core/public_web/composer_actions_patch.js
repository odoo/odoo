import { composerActionsRegistry } from "@mail/core/common/composer_actions";
import { CreatePollDialog } from "@mail/core/common/create_poll_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

composerActionsRegistry.add("start-poll", {
    name: _t("Start a poll"),
    icon: "fa fa-bar-chart",
    onClick: (component) => {
        this.dialogService.add(CreatePollDialog, {
            title: _t("Create a Poll"),
            confirmText: _t("Post"),
            size: "md",
            thread: component.thread,
        });
    },
    setup: (action) => {
        this.dialogService = useService("dialog");
    },
});
