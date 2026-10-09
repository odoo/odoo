import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { Component, onWillStart, proxy } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { _t } from "@web/core/l10n/translation";

async function updatePosKanbanViewState(orm, stateObj) {
    const result = await orm
        .cache({ type: "disk" })
        .call("pos.config", "get_pos_kanban_view_state");
    Object.assign(stateObj, result);
}

/**
 * Onboarding scenarios to create a first point of sale, displayed by the help
 * view of the point of sale dashboard (see `pos_config_view_help`).
 */
export class PosOnboardingScenarios extends Component {
    static template = "point_of_sale.PosOnboardingScenarios";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.posState = proxy({
            has_pos_config: true,
            has_chart_template: true,
            is_restaurant_installed: true,
            is_main_company: true,
        });
        onWillStart(() => updatePosKanbanViewState(this.orm, this.posState));
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
    }

    async clickLoadScenario(item) {
        await this.loadScenario.call(item);
        if (this.loadScenario.status == "error") {
            throw this.loadScenario.result;
        }
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
                    body: _t("It seems like you do not have enough rights to create a shop."),
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
                iconFile: "clothes-icon.svg",
            },
            {
                name: _t("Furniture"),
                description: _t("Stock, product configurator, replenishment, discounts"),
                functionName: "load_onboarding_furniture_scenario",
                iconFile: "furniture-icon.svg",
            },
            {
                name: _t("Bakery"),
                description: _t("Food, but over the counter"),
                functionName: "load_onboarding_bakery_scenario",
                iconFile: "bakery-icon.svg",
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
                iconFile: "restaurant-icon.svg",
            },
            {
                name: _t("Bar"),
                isRestaurant: true,
                description: _t("Floor plan, tips, self order, etc."),
                functionName: "load_onboarding_bar_scenario",
                iconFile: "cocktail-icon.svg",
            },
        ];
    }

    get retailScenario() {
        return {
            name: _t("Retail"),
            isRestaurant: false,
            description: _t("Any shop"),
            functionName: "load_onboarding_retail_scenario",
            iconFile: "retail-icon.svg",
        };
    }
}

registry.category("view_widgets").add("pos_onboarding_scenarios", {
    component: PosOnboardingScenarios,
});
