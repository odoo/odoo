import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "../../core/l10n/translation";
import { formatDateTime } from "@web/core/l10n/dates";
import { useLayoutEffect } from "@web/owl2/utils";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const { DateTime } = luxon;

class OfflineSystray extends Component {
    static template = "web.OfflineSystray";
    static props = {};
    static components = { Dropdown, DropdownItem };

    setup() {
        this.offlineService = useService("offline");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        useLayoutEffect(this.env.redrawNavbar, () => [
            this.offlineService.offline,
            this.offlineService.hasScheduledCalls,
        ]);
    }

    get groupEntries() {
        const items = [];
        for (const { key, value } of Object.values(this.offlineService.scheduledORM)) {
            // OfflineSystray for the moment only support web_save!
            if (value.method === "web_save") {
                let tooltipDetails = Object.entries(value.extras.changes);
                if (value.args[0].length) {
                    tooltipDetails = tooltipDetails.map((c) => [
                        c[0],
                        value.extras.originalValues[c[0]],
                        c[1],
                    ]);
                }
                const status = value.args[0].length ? _t("Edited") : _t("Created");
                const statusColor = value.args[0].length ? "2" : "10";
                items.push({
                    id: key,
                    timeStamp: value.extras.timeStamp,
                    actionName: value.extras.actionName,
                    displayName: value.extras.displayName,
                    status,
                    statusColor,
                    clickable: this.isClickable(value),
                    error: value.extras.error,
                    tooltip: JSON.stringify({
                        timeStamp: formatDateTime(DateTime.fromMillis(value.extras.timeStamp)),
                        details: tooltipDetails,
                    }),
                });
            }
        }
        const sections = Object.entries(Object.groupBy(items, (item) => item.actionName || ""));
        sections.forEach(([_name, items]) => {
            items.sort((itemA, itemB) => itemA.timeStamp - itemB.timeStamp);
        });
        return sections;
    }

    isClickable(value) {
        const resId = value.args[0].length ? value.args[0][0] : false;
        return (
            value.extras.viewType === "form" &&
            (!this.offlineService.offline ||
                this.offlineService.isAvailableOffline(value.extras.actionId, "form", resId))
        );
    }

    get inError() {
        return Object.values(this.offlineService.scheduledORM).find(
            ({ value }) => value.extras.error
        );
    }

    get labelColor() {
        if (this.inError) {
            if (this.env.isSmall) {
                return "text-danger";
            }
            return "text-bg-danger";
        }
        if (this.offlineService.offline) {
            if (this.env.isSmall) {
                return "text-warning";
            }
            return "text-bg-warning";
        }
        if (this.offlineService.syncingORM) {
            if (this.env.isSmall) {
                return "";
            }
            return "text-bg-secondary";
        }
        return "text-bg-secondary";
    }

    get labelIcon() {
        if (this.offlineService.syncingORM) {
            return "spinner-border";
        }
        if (this.inError) {
            return "fa fa-exclamation-circle";
        }
        if (this.offlineService.offline) {
            return "fa fa-chain-broken";
        }
        return "spinner-border";
    }

    get labelText() {
        if (this.offlineService.syncingORM) {
            return _t("Syncing");
        }
        if (this.offlineService.offline) {
            return _t("Working offline");
        }
        if (this.inError) {
            return _t("Sync issues");
        }
        return _t("Syncing");
    }

    discard(id) {
        this.dialogService.add(ConfirmationDialog, {
            title: _t("Discard offline change"),
            body: _t("Are you sure that you want to discard the changes you made offline?"),
            confirmLabel: _t("Discard"),
            cancelLabel: _t("No, keep it"),
            confirm: () => this.offlineService.removeScheduledORM(id),
            cancel: () => {},
        });
    }

    async openView(id) {
        const { value } = this.offlineService.scheduledORM[id];
        const resId = value.args[0]?.[0];
        await this.actionService.doAction(value.extras.actionId, {
            viewType: "form",
            props: { offlineId: id, resId },
            clearBreadcrumbs: true,
        });
        if (!this.offlineService.offline) {
            this.offlineService.removeScheduledORM(id);
        }
    }
}

const offlineSystrayItem = {
    Component: OfflineSystray,
};

registry.category("systray").add("offline", offlineSystrayItem, { sequence: 1000 });
