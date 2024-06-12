/** @odoo-module */

import { Spreadsheet } from "@odoo/o-spreadsheet";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { loadBundle, templates } from "@web/core/assets";
import { PublicReadonlySpreadsheet } from "@spreadsheet/public_readonly_app/public_readonly";

import { App } from "@odoo/owl";
import { registry } from "@web/core/registry";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

/**
 * Mount o-spreadsheet component with the given spreadsheet model
 * @param {Model} model
 * @returns {Promise<HTMLElement>}
 */
export async function mountSpreadsheet(model) {
    await loadBundle("web.chartjs_lib");
    const app = new App(Spreadsheet, {
        props: { model },
        templates: templates,
        env: model.config.custom.env,
        test: true,
    });
    registerCleanup(() => app.destroy());
    const fixture = getFixture();
    await app.mount(fixture);
    return fixture;
}

/**
 * Mount public spreadsheet component with the given data
 * @param {Model} model
 * @returns {Promise<HTMLElement>}
 */
export async function mountPublicSpreadsheet(data, dataUrl, mode) {
    const serviceRegistry = registry.category("services");
    const fakeHTTPService = {
        start() {
            return {
                get: (route, params) => {
                    if (route === dataUrl) {
                        return data;
                    }
                },
            };
        },
    };
    serviceRegistry.add("http", fakeHTTPService);
    const env = await makeTestEnv();
    const app = new App(PublicReadonlySpreadsheet, {
        props: { dataUrl, downloadExcelUrl: "downloadUrl", mode },
        templates,
        env,
        test: true,
    });
    registerCleanup(() => app.destroy());
    const fixture = getFixture();
    await app.mount(fixture);
    return fixture;
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

export async function keyDown(eventArgs) {
    const ev = new KeyboardEvent("keydown", { bubbles: true, cancelable: true, ...eventArgs });
    document.activeElement.dispatchEvent(ev);
    return await nextTick();
}
