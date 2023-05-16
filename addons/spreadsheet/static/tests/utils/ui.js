/** @odoo-module */

import { Spreadsheet } from "@odoo/o-spreadsheet";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { loadJS, templates } from "@web/core/assets";

import { App } from "@odoo/owl";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

/**
 * Mount o-spreadsheet component with the given spreadsheet model
 * @param {Model} model
 * @returns {Promise<HTMLElement>}
 */
export async function mountSpreadsheet(model) {
    await loadJS("/web/static/lib/Chart/Chart.js");
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

export async function doMenuAction(registry, path, env) {
    await getMenuItem(registry, path, env).execute(env);
}

function getMenuItem(registry, _path, env) {
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
