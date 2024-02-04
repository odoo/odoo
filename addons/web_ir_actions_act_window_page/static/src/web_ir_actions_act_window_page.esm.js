/** @odoo-module **/
// (c) 2013-2015 Therp BV (<http://therp.nl>)
// (c) 2023 Hunki Enterprises BV (<https://hunki-enterprises.com>)
// License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import {Pager} from "@web/core/pager/pager";
import {patch} from "@web/core/utils/patch";
import {registry} from "@web/core/registry";
import {useBus} from "@web/core/utils/hooks";

const actionHandlersRegistry = registry.category("action_handlers");

async function executeWindowActionPage({env}, direction) {
    return env.bus.trigger("pager:navigate", {direction});
}

async function executeWindowActionList({env}) {
    return env.services.action.switchView("list");
}

actionHandlersRegistry.add("ir.actions.act_window.page.prev", async (params) =>
    executeWindowActionPage(params, -1)
);
actionHandlersRegistry.add("ir.actions.act_window.page.next", async (params) =>
    executeWindowActionPage(params, 1)
);
actionHandlersRegistry.add("ir.actions.act_window.page.list", async (params) =>
    executeWindowActionList(params)
);

patch(Pager.prototype, "navigate event listener", {
    setup() {
        this._super.apply();
        const handleNavigate = (ev) => this._handleNavigate(ev);
        useBus(this.env.bus, "pager:navigate", handleNavigate);
    },
    _handleNavigate(ev) {
        return this.navigate(ev.detail.direction);
    },
});
