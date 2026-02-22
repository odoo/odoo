import { Component, onWillStart } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

function runUnitTestsItem() {
    const href = "/web/tests?debug=assets";
    return {
        type: "item",
        description: _t("Run Unit Tests"),
        href,
        callback: () => browser.open(href),
        sequence: 450,
        section: "testing",
    };
}

export function openViewItem({ env }) {
    async function onSelected(records) {
        const views = await env.services.orm.searchRead(
            "ir.ui.view",
            [["id", "=", records[0]]],
            ["name", "model", "type"],
            { limit: 1 }
        );
        const view = views[0];
        env.services.action.doAction({
            type: "ir.actions.act_window",
            name: view.name,
            res_model: view.model,
            views: [[view.id, view.type]],
        });
    }

    return {
        type: "item",
        description: _t("Open View"),
        callback: () => {
            env.services.dialog.add(SelectCreateDialog, {
                resModel: "ir.ui.view",
                title: _t("Select a view"),
                multiSelect: false,
                domain: [
                    ["type", "!=", "qweb"],
                    ["type", "!=", "search"],
                ],
                onSelected,
            });
        },
        sequence: 540,
        section: "tools",
    };
}

class ClocReport extends Component {
    static components = { Dialog };
    static template = "web.ClocReport";
    static props = {
        close: Function,
    };
    setup() {
        this.action = useService("action");
        onWillStart(async () => {
            const data = await this.fetchCloc();
            this.data = data;
            this.records = this.sortRecords(data.records);
        });
    }

    sortRecords(records) {
        const compare = (a, b) =>
            b.billable - a.billable ||
            b.code_lines - a.code_lines ||
            (a.model || a.display_name).localeCompare(b.model || b.display_name);
        return records.toSorted(compare);
    }

    fetchCloc() {
        return rpc("/web/cloc");
    }

    viewRecord(record, isMiddleClick) {
        const target = isMiddleClick ? "main" : "new";
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                res_id: record.id,
                res_model: record.model,
                target,
            },
            {
                newWindow: isMiddleClick,
            }
        );
    }
}

function clocReport({ env }) {
    if (user.isAdmin) {
        return {
            type: "item",
            description: "Count LoC",
            sequence: 541,
            section: "tools",
            callback: () => {
                env.services.dialog.add(ClocReport, {});
            },
        };
    }
}

registry
    .category("debug")
    .category("default")
    .add("runUnitTestsItem", runUnitTestsItem)
    .add("openViewItem", openViewItem)
    .add("clocReport", clocReport);
