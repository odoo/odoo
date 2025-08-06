import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

threadActionsRegistry
    .add("mark-all-read", {
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
        setup() {
            const component = useComponent();
            component.orm = useService("orm");
        },
    })
    .add("unstar-all", {
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
        setup() {
            const component = useComponent();
            component.store = useService("mail.store");
        },
        name: _t("Unstar all"),
    });
