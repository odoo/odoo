import { Model, Spreadsheet, stores } from "@odoo/o-spreadsheet";
import { loadBundle } from "@web/core/assets";

import { getFixture } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml, onMounted, onWillUnmount } from "@odoo/owl";
import { useSpreadsheetNotificationStore } from "@spreadsheet/hooks";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";

const { useStoreProvider, ModelStore } = stores;
class Parent extends Component {
    // MainComponentsContainer is used to have target for odoo components
    static template = xml`
        <MainComponentsContainer/>
        <Spreadsheet model="this.props.model"/>
    `;
    static components = { Spreadsheet, MainComponentsContainer };
    static props = { model: Model };
    setup() {
        useSpreadsheetNotificationStore();

        const stores = useStoreProvider();
        stores.inject(ModelStore, this.props.model);
        onMounted(() => {
            this.props.model.on("update", this, () => this.render(true));
            stores.on("store-updated", this, this.render.bind(this, true));
        });
        onWillUnmount(() => {
            this.props.model.off("update", this);
            stores.off("store-updated", this);
        });
    }
}

/**
 * Mount o-spreadsheet component with the given spreadsheet model
 * @param {Model} model
 * @returns {Promise<HTMLElement>}
 */
export async function mountSpreadsheet(model) {
    // const serviceRegistry = registry.category("services");
    // serviceRegistry.add("dialog", makeFakeDialogService(), { force: true });
    // serviceRegistry.add("notification", makeFakeNotificationService(), { force: true });
    await loadBundle("web.chartjs_lib");
    mountWithCleanup(Parent, {
        props: {
            model,
        },
        env: model.config.custom.env,
        noMainContainer: true,
    });
    await animationFrame();
    return getFixture();
}

export async function doMenuAction(registry, path, env) {
    await getActionMenu(registry, path, env).execute(env);
}

export function getActionMenu(registry, _path, env) {
    const path = [..._path];
    let items = registry.getMenuItems();
    while (items.length && path.length) {
        const id = path.shift();
        const item = items.find((item) => item.id === id);
        if (!item) {
            throw new Error(`Menu item ${id} not found`);
        }
        if (path.length === 0) {
            return item;
        }
        items = item.children(env);
    }
    throw new Error(`Menu item not found`);
}
