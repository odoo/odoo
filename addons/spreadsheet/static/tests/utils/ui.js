/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { getFixture } from "@web/../tests/helpers/utils";
import { loadJS, templates } from "@web/core/assets";

const { App } = owl;
const { Spreadsheet } = spreadsheet;
const { getMenuChildren } = spreadsheet.helpers;

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
        env: model.config.evalContext.env,
        test: true,
    });
    registerCleanup(() => app.destroy());
    const fixture = getFixture();
    await app.mount(fixture);
    return fixture;
}

export async function doMenuAction(registry, path, env) {
    const root = path[0];
    let node = registry.get(root);
    for (const p of path.slice(1)) {
        const children = getMenuChildren(node, env);
        node = children.find((child) => child.id === p);
    }
    if (!node) {
        throw new Error(`Cannot find menu with path "${path.join("/")}"`);
    }
    await node.action(env);
}
