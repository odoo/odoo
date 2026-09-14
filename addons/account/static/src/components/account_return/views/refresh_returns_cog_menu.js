/** @odoo-module native */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { COG_GROUP, isActWindowView } from "@web/search/cog_menu/cog_menu_group";
import { CogMenuItem } from "@web/search/cog_menu/cog_menu_item";

const cogMenuRegistry = registry.category("cogMenu");

export class RefreshAccountReturns extends Component {
    static template = "account.RefreshAccountReturns";
    static components = { CogMenuItem };
    static props = {};

    async refresh_all_account_returns() {
        await this.env.services.orm.call(
            "account.return",
            "action_refresh_all_returns",
        );
        await this.env.model.load();
    }
}

export const refreshAccountReturns = {
    Component: RefreshAccountReturns,
    groupNumber: COG_GROUP.APP,
    isDisplayed: (env) =>
        isActWindowView(env, ["kanban"]) &&
        env.config.viewSubType === "account_return_kanban",
};

cogMenuRegistry.add("refresh-account-returns-menu", refreshAccountReturns, {
    sequence: 10,
});
