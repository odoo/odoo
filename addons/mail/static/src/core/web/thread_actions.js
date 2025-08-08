import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

registerThreadAction("mark-all-read", {
    condition(component) {
        return component.thread?.id === "inbox";
    },
    disabledCondition(component) {
        return component.thread.isEmpty;
    },
    open(component) {
        component.orm.silent.call("mail.message", "mark_all_as_read");
    },
    sequence: 1,
    name: _t("Mark all read"),
    setup(component) {
        component.orm = useService("orm");
    },
});
registerThreadAction("unstar-all", {
    condition(component) {
        return component.thread?.id === "starred";
    },
    disabledCondition(component) {
        return component.thread.isEmpty;
    },
    open(component) {
        component.store.unstarAll();
    },
    sequence: 2,
    setup(component) {
        component.store = useService("mail.store");
    },
    name: _t("Unstar all"),
});
