import { Model, Spreadsheet, stores } from "@odoo/o-spreadsheet";
import { loadBundle } from "@web/core/assets";

import { getFixture } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, onMounted, onWillUnmount, t, useProps, xml } from "@odoo/owl";
import { useSpreadsheetNotificationPlugin } from "@spreadsheet/hooks";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { render, useSubEnv } from "@web/owl2/utils";

const { useStoreProvider, ModelStore } = stores;

class Parent extends Component {
    static template = xml`<Spreadsheet model="this.props.model"/>`;
    static components = { Spreadsheet, MainComponentsContainer };
    props = useProps({
        model: t.instanceOf(Model),
    });
    setup() {
        useSpreadsheetNotificationPlugin();
    }
}

class ComponentWithStores extends Component {
    static template = xml`<t t-component="this.props.component" t-props="this.props.props"/>`;
    props = useProps({
        component: t.component(),
        props: t.object(),
        model: t.instanceOf(Model),
    });
    setup() {
        const stores = useStoreProvider();
        stores.inject(ModelStore, this.props.model);
        useSubEnv({
            model: this.props.model,
        });
        onMounted(() => {
            this.props.model.on("update", this, () => render(this, true));
            stores.on("store-updated", this, () => render(this, true));
        });
        onWillUnmount(() => {
            this.props.model.off("update", this);
            stores.off("store-updated", this);
        });
    }
}

export async function mountComponentWithStores(component, model, props = {}) {
    await mountWithCleanup(ComponentWithStores, {
        props: {
            component,
            props,
            model,
        },
        componentEnv: model.config.custom.env,
        noMainContainer: false,
    });
    await animationFrame();
    return getFixture();
}

/**
 * Mount o-spreadsheet component with the given spreadsheet model
 * @param {Model} model
 * @returns {Promise<HTMLElement>}
 */
export async function mountSpreadsheet(model) {
    await loadBundle("web.chartjs_lib");
    return mountComponentWithStores(Parent, model, { model });
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
