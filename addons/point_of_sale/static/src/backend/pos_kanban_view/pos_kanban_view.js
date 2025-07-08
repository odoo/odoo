import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { cookie } from "@web/core/browser/cookie";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { onWillStart, useState, onWillRender } from "@odoo/owl";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { _t } from "@web/core/l10n/translation";
import { KanbanController } from "@web/views/kanban/kanban_controller";

async function updatePosKanbanViewState(orm, stateObj) {
    const result = await orm.call("pos.config", "get_pos_kanban_view_state");
    Object.assign(stateObj, result);
}

export class PosKanbanController extends KanbanController {
    static template = "point_of_sale.PosKanbanController";
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.initialPosState = {
            has_pos_config: true,
            has_chart_template: true,
            is_restaurant_installed: true,
            show_predefined_scenarios: true,
            is_main_company: true,
        };
        onWillStart(() => updatePosKanbanViewState(this.orm, this.initialPosState));
    }
}

export class PosKanbanRenderer extends KanbanRenderer {
    static template = "point_of_sale.PosKanbanRenderer";
    static props = [...KanbanRenderer.props, "initialPosState"];

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.posState = useState(this.props.initialPosState);
        this.loadScenario = useTrackedAsync(
            async ({ functionName, isRestaurant }) =>
                await this.callWithViewUpdate(async () => {
                    let isInstalledWithDemo = false;
                    if (isRestaurant && !this.posState.is_restaurant_installed) {
                        const result = await this.orm.call("pos.config", "install_pos_restaurant");
                        isInstalledWithDemo = result.installed_with_demo;
                    }
                    if (
                        !isInstalledWithDemo ||
                        (isInstalledWithDemo && !this.posState.is_main_company)
                    ) {
                        // load onboarding scenario without demo data
                        const result = await this.orm.call("pos.config", functionName, [false]);
                        return result;
                    }
                })
        );

        onWillRender(() => this.checkDisplayedResult());
    }

    async clickLoadScenario(item) {
        await this.loadScenario.call(item);
        if (this.loadScenario.status == "error") {
            throw this.loadScenario.result;
        }
    }

    checkDisplayedResult() {
        this.posState.show_predefined_scenarios = this.props.list.count === 0;
    }

    get isDarkTheme() {
        return cookie.get("color_scheme") === "dark";
    }

    async callWithViewUpdate(func) {
        try {
            const [isPosManager, isAdmin] = await Promise.all([
                user.hasGroup("point_of_sale.group_pos_manager"),
                user.hasGroup("base.group_system"),
            ]);

            if (!(isPosManager && isAdmin)) {
                this.dialog.add(AlertDialog, {
                    title: _t("Access Denied"),
                    body: _t(
                        "It seems like you don't have enough rights to create point of sale configurations."
                    ),
                });
                return;
            }
            const result = await func();
            await updatePosKanbanViewState(this.orm, this.posState);
            return result;
        } finally {
            this.env.searchModel.clearQuery();
        }
    }

    get shopScenarios() {
        return [
            {
                name: _t("Clothes"),
                description: _t("Multi colors and sizes"),
                functionName: "load_onboarding_clothes_scenario",
                iconFile: this.isDarkTheme ? "clothes-icon-dark.png" : "clothes-icon.png",
            },
            {
                name: _t("Furniture"),
                description: _t("Stock, product configurator, replenishment, discounts"),
                functionName: "load_onboarding_furniture_scenario",
                iconFile: this.isDarkTheme ? "furniture-icon-dark.png" : "furniture-icon.png",
            },
            {
                name: _t("Bakery"),
                description: _t("Food, but over the counter"),
                functionName: "load_onboarding_bakery_scenario",
                iconFile: this.isDarkTheme ? "bakery-icon-dark.png" : "bakery-icon.png",
            },
        ];
    }

    get restaurantScenarios() {
        return [
            {
                name: _t("Restaurant"),
                isRestaurant: true,
                description: _t("Tables, menus, kitchen display, etc."),
                functionName: "load_onboarding_restaurant_scenario",
                iconFile: this.isDarkTheme ? "restaurant-icon-dark.png" : "restaurant-icon.png",
            },
            {
                name: _t("Bar"),
                isRestaurant: true,
                description: _t("Floor plan, tips, self order, etc."),
                functionName: "load_onboarding_bar_scenario",
                iconFile: this.isDarkTheme ? "cocktail-icon-dark.png" : "cocktail-icon.png",
            },
        ];
    }

    get retailScenario() {
        return {
            name: _t("Retail"),
            isRestaurant: false,
            description: _t("Any shop"),
            functionName: "load_onboarding_retail_scenario",
            iconFile: this.isDarkTheme ? "retail-icon-dark.png" : "retail-icon.png",
        };
    }

    showTopBorder() {
        const { model } = this.props.list;
        return model.hasData();
    }

    get showNoContentHelper() {
        return false;
    }
}

export const PosKanbanView = {
    ...kanbanView,
    Renderer: PosKanbanRenderer,
    Controller: PosKanbanController,
};

registry.category("views").add("pos_config_kanban_view", PosKanbanView);
