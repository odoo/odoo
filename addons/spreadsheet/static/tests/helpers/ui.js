import { Model, Spreadsheet } from "@odoo/o-spreadsheet";
import { loadBundle } from "@web/core/assets";

import { getFixture } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { useSpreadsheetNotificationStore } from "@spreadsheet/hooks";
import { PublicReadonlySpreadsheet } from "@spreadsheet/public_readonly_app/public_readonly";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

class Parent extends Component {
    static template = xml`<Spreadsheet model="props.model"/>`;
    static components = { Spreadsheet };
    static props = { model: Model };
    setup() {
        useSpreadsheetNotificationStore();
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

/**
 * Mount public spreadsheet component with the given data
 * @returns {Promise<HTMLElement>}
 */
export async function mountPublicSpreadsheet(dataUrl, mode) {
    mountWithCleanup(PublicReadonlySpreadsheet, {
        props: {
            dataUrl,
            downloadExcelUrl: "downloadUrl",
            mode,
        },
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
