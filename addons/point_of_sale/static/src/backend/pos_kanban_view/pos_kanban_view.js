/** @odoo-module native */
import { onWillStart, useState } from "@odoo/owl";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { colorScheme } from "@web/core/color_scheme";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/ui/dialog";
import { KanbanController, KanbanRenderer, kanbanView } from "@web/views/kanban";
const log = makeLogger("pos.backend.kanban");
async function updatePosKanbanViewState(orm, stateObj) {
    const result = await log.measure("get_pos_kanban_view_state", () =>
        orm.call("pos.config", "get_pos_kanban_view_state"),
    );
    Object.assign(stateObj, result);
    log.logic("pos kanban state", () => result);
}

export class PosKanbanModel extends kanbanView.Model {
    setup(...args) {
        super.setup(...args);
        this.pendingLoads = 0;
    }

    async load(params) {
        this.pendingLoads++;
        this.notify();
        try {
            return await super.load(params);
        } finally {
            this.pendingLoads--;
            this.notify();
        }
    }
}

export class PosKanbanController extends KanbanController {
    static template = "point_of_sale.PosKanbanController";
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.initialPosState = {
            has_pos_config: true,
            has_chart_template: true,
            is_restaurant_installed: true,
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
        this.loadScenario = useTrackedAsync(async ({ functionName, isRestaurant }) =>
            this.callWithViewUpdate(async () => {
                let isInstalledWithDemo = false;
                log.pipeline("loadScenario", () => ({
                    functionName,
                    isRestaurant,
                    restaurantInstalled: this.posState.is_restaurant_installed,
                    mainCompany: this.posState.is_main_company,
                }));
                if (isRestaurant && !this.posState.is_restaurant_installed) {
                    const result = await log.measure("install_pos_restaurant", () =>
                        this.orm.call("pos.config", "install_pos_restaurant"),
                    );
                    isInstalledWithDemo = result.installed_with_demo;
                }
                const runScenario =
                    !isInstalledWithDemo || !this.posState.is_main_company;
                log.logic("loadScenario: run", () => ({
                    functionName,
                    isInstalledWithDemo,
                    runScenario,
                }));
                if (runScenario) {
                    return log.measure(functionName, () =>
                        this.orm.call("pos.config", functionName, [false]),
                    );
                }
            }),
        );
    }

    async clickLoadScenario(item) {
        if (this.isScenarioDisabled) {
            log.logic("loadScenario: disabled");
            return;
        }
        await this.loadScenario.call(item);
        if (this.loadScenario.status === "error") {
            throw this.loadScenario.result;
        }
    }

    get isScenarioDisabled() {
        return (
            !this.posState.has_chart_template ||
            this.loadScenario.status === "loading" ||
            this.props.list.model.pendingLoads > 0
        );
    }

    get showPredefinedScenarios() {
        return this.props.list.count === 0;
    }

    get isDarkTheme() {
        return colorScheme.isDark;
    }

    async callWithViewUpdate(func) {
        const [isPosManager, isAdmin] = await Promise.all([
            user.hasGroup("point_of_sale.group_pos_manager"),
            user.hasGroup("base.group_system"),
        ]);

        log.logic("callWithViewUpdate: rights", () => ({ isPosManager, isAdmin }));
        if (!(isPosManager && isAdmin)) {
            this.dialog.add(AlertDialog, {
                title: _t("Access Denied"),
                body: _t(
                    "It seems like you don't have enough rights to create point of sale configurations.",
                ),
            });
            return;
        }
        let result;
        const errors = [];
        try {
            result = await func();
            await updatePosKanbanViewState(this.orm, this.posState);
        } catch (error) {
            errors.push(error);
        }
        try {
            await this.env.searchModel.clearQuery();
        } catch (error) {
            errors.push(error);
        }
        if (errors.length) {
            if (errors.length > 1) {
                log.logic("search refresh also failed after onboarding error", () => ({
                    error: errors[1],
                }));
            }
            throw errors[0];
        }
        return result;
    }

    get shopScenarios() {
        return [
            {
                name: _t("Clothes"),
                description: _t("Multi colors and sizes"),
                functionName: "load_onboarding_clothes_scenario",
                iconFile: this.isDarkTheme
                    ? "clothes-icon-dark.png"
                    : "clothes-icon.png",
            },
            {
                name: _t("Furniture"),
                description: _t(
                    "Stock, product configurator, replenishment, discounts",
                ),
                functionName: "load_onboarding_furniture_scenario",
                iconFile: this.isDarkTheme
                    ? "furniture-icon-dark.png"
                    : "furniture-icon.png",
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
                iconFile: this.isDarkTheme
                    ? "restaurant-icon-dark.png"
                    : "restaurant-icon.png",
            },
            {
                name: _t("Bar"),
                isRestaurant: true,
                description: _t("Floor plan, tips, self order, etc."),
                functionName: "load_onboarding_bar_scenario",
                iconFile: this.isDarkTheme
                    ? "cocktail-icon-dark.png"
                    : "cocktail-icon.png",
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
    Model: PosKanbanModel,
    Renderer: PosKanbanRenderer,
    Controller: PosKanbanController,
};

registry.category("views").add("pos_config_kanban_view", PosKanbanView);
