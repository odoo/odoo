import { Component, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { groupBy, sortBy } from "@web/core/utils/arrays";
import { _t } from "../../core/l10n/translation";
import { formatDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

class OfflineSystray extends Component {
    static template = "web.OfflineSystray";
    static props = {};
    static components = { Dropdown, DropdownItem };

    setup() {
        this.offlineService = useService("offline");
        this.actionService = useService("action");
        this.menuService = useService("menu");
        useEffect(this.env.redrawNavbar, () => [
            this.offlineService.offline,
            this.offlineService.hasScheduledCalls,
        ]);
    }

    get groupEntries() {
        const items = [];
        for (const { key, value } of Object.values(this.offlineService.scheduledORM)) {
            // OfflineSystray for the moment only support web_save!
            if (value.method === "web_save") {
                const status = value.args[0].length ? _t("Edited") : _t("Created");
                const statusColor = value.args[0].length ? "1" : "10";
                items.push({
                    id: key,
                    actionName: value.extras.actionName,
                    displayName: value.extras.displayName,
                    status,
                    statusColor,
                    clickable: value.extras.viewType === "form",
                    error: value.extras.error,
                    tooltip: JSON.stringify({
                        status,
                        timeStamp: formatDateTime(DateTime.fromMillis(value.extras.timeStamp)),
                        changes: Object.entries(value.extras.changes),
                    }),
                });
            }
        }
        const sections = groupBy(items, (item) => item.actionName || "");
        return sortBy(Object.entries(sections), ([section]) => section);
    }

    get inError() {
        return Object.values(this.offlineService.scheduledORM).find(
            ({ value }) => value.extras.error
        );
    }

    get classNames() {
        return {
            fa: true,
            "fa-chain-broken": !this.inError,
            "fa-exclamation": this.inError,
            o_nav_entry: true,
            "text-danger": true,
        };
    }

    get labelText() {
        if (this.inError) {
            return _t("Sync Issues");
        }
        if (this.offlineService.offline) {
            return _t("Working offline");
        }
        return _t("Syncing");
    }

    async openView(id) {
        const { value } = this.offlineService.scheduledORM[id];
        if (value.extras.menuId) {
            this.menuService.setCurrentMenu(value.extras.menuId);
        }
        const resId = value.args[0]?.[0];
        await this.actionService.doAction(value.extras.actionId, {
            viewType: "form",
            props: { offlineId: id, resId },
            clearBreadcrumbs: true,
        });
        this.offlineService.removeScheduledORM(id);
    }
}

const offlineSystrayItem = {
    Component: OfflineSystray,
};

registry.category("systray").add("offline", offlineSystrayItem, { sequence: 1000 });
