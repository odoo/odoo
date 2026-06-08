import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

const BUTTON_CONFIG = {
    fetch: {
        action: "button_fetch_in_einvoices",
        field: "show_fetch_in_einvoices_button",
        journalType: "purchase",
        moveTypePrefix: "in_",
        label: _t("Fetch e-Invoices"),
    },
    refresh: {
        action: "button_refresh_out_einvoices_status",
        field: "show_refresh_out_einvoices_status_button",
        journalType: "sale",
        moveTypePrefix: "out_",
        label: _t("Refresh e-Invoices Status"),
    },
};

function getButtonConfig(searchModel) {
    const { globalContext, context } = searchModel;
    const defaultMoveType = context.default_move_type || "";
    for (const buttonConfig of Object.values(BUTTON_CONFIG)) {
        if (globalContext[buttonConfig.field] || defaultMoveType.startsWith(buttonConfig.moveTypePrefix)) {
            return buttonConfig;
        }
    }

    return null;
}

async function getVisibleJournalIds(searchModel, buttonConfig, domain) {
    const journals = await searchModel.orm.searchRead(
        "account.journal",
        domain,
        ["id", buttonConfig.field],
        { context: searchModel.context }
    );
    return journals.filter((j) => j[buttonConfig.field]).map((j) => j.id);
}

async function getRelevantJournalIds(searchModel, buttonConfig = getButtonConfig(searchModel)) {
    if (!buttonConfig) {
        return [];
    }

    const journalId = searchModel.globalContext.default_journal_id;
    if (journalId) {
        if (searchModel.globalContext[buttonConfig.field]) {
            return [journalId];
        }

        return getVisibleJournalIds(searchModel, buttonConfig, [["id", "=", journalId]]);
    }

    // The button-visibility fields are computed/unstored, so filter after reading.
    return getVisibleJournalIds(searchModel, buttonConfig, [["type", "=", buttonConfig.journalType]]);
}

async function getActionData(searchModel) {
    const buttonConfig = getButtonConfig(searchModel);
    if (!buttonConfig) {
        return null;
    }

    const journalIds = await getRelevantJournalIds(searchModel, buttonConfig);
    if (!journalIds.length) {
        return null;
    }

    return { buttonConfig, journalIds };
}

export class FetchEInvoices extends Component {
    static template = "account.FetchEInvoices";
    static props = {};
    static components = { DropdownItem };

    setup() {
        super.setup();
        this.action = useService("action");
    }

    get buttonConfig() {
        return getButtonConfig(this.env.searchModel);
    }

    get buttonLabel() {
        return this.buttonConfig?.label;
    }

    async fetchEInvoices() {
        const actionData = await getActionData(this.env.searchModel);
        if (!actionData) {
            return;
        }

        const { buttonConfig, journalIds } = actionData;

        await this.action.doActionButton({
            type: "object",
            resIds: journalIds,
            name: buttonConfig.action,
            resModel: "account.journal",
            onClose: () => window.location.reload(),
        });
    }
}

export const fetchEInvoicesActionMenu = {
    Component: FetchEInvoices,
    groupNumber: ACTIONS_GROUP_NUMBER,
    isDisplayed: async ({ searchModel }) => {
        if (searchModel.resModel !== "account.move") {
            return false;
        }

        return Boolean(await getActionData(searchModel));
    },
};

cogMenuRegistry.add("account-fetch-e-invoices", fetchEInvoicesActionMenu, { sequence: 11 });
