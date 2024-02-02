/** @odoo-module */

import { Model, Spreadsheet } from "@odoo/o-spreadsheet";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { loadBundle } from "@web/core/assets";
import { getTemplate } from "@web/core/templates";
import { PublicReadonlySpreadsheet } from "@spreadsheet/public_readonly_app/public_readonly";

import { App, Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useSpreadsheetNotificationStore } from "@spreadsheet/hooks";
import {
    makeFakeDialogService,
    makeFakeNotificationService,
} from "@web/../tests/legacy/helpers/mock_services";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

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
    const serviceRegistry = registry.category("services");
    serviceRegistry.add("dialog", makeFakeDialogService(), { force: true });
    serviceRegistry.add("notification", makeFakeNotificationService(), { force: true });
    await loadBundle("web.chartjs_lib");
    const app = new App(Parent, {
        props: { model },
        getTemplate,
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
    serviceRegistry.add("dialog", makeFakeDialogService(), { force: true });
    serviceRegistry.add("notification", makeFakeNotificationService(), { force: true });
    const env = await makeTestEnv();
    const app = new App(PublicReadonlySpreadsheet, {
        props: { dataUrl, downloadExcelUrl: "downloadUrl", mode },
        getTemplate,
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
