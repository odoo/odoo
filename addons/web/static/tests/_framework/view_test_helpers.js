/** @odoo-module */

import { waitFor } from "@odoo/hoot-dom";
import { Component, useSubEnv, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { View, getDefaultConfig } from "@web/views/view";
import { mountWithCleanup } from "./component_test_helpers";
import { contains } from "./dom_test_helpers";
import { getMockEnv, getService, makeMockEnv } from "./env_test_helpers";
import { MockServer } from "./mock_server/mock_server";

/**
 * @typedef {{
 *  arch?: string;
 *  config?: Record<string, any>;
 *  env?: import("@web/env").OdooEnv;
 *  searchViewArch?: string;
 *  type: ViewType;
 *  [key: string]: any;
 * }} MountViewParams
 *
 * @typedef {{
 *  class?: string;
 *  id?: string;
 *  index?: number;
 *  modifier?: string;
 *  target?: string;
 *  text?: string;
 * }} SelectorOptions
 *
 * @typedef {import("./mock_server/mock_model").ViewType} ViewType
 */

//-----------------------------------------------------------------------------
// Internals
//-----------------------------------------------------------------------------

/**
 *
 * @param {string} base
 * @param {SelectorOptions} [params]
 */
const buildSelector = (base, params) => {
    let selector = base;
    params ||= {};
    if (params.id) {
        selector += `#${params.id}`;
    }
    if (params.class) {
        selector += `.${params.class}`;
    }
    if (params.modifier) {
        selector += `:${params.modifier}`;
    }
    if (params.text) {
        selector += `:contains(${params.text})`;
    }
    if (params.index) {
        selector += `:eq(${params.index})`;
    }
    if (params.target) {
        selector += ` ${params.target}`;
    }
    return selector;
};

/**
 * @param {MountViewParams} params
 * @returns {typeof View.props}
 */
const parseViewProps = (params) => {
    // View & search view arch
    if (
        "arch" in params ||
        "searchViewArch" in params ||
        "searchViewId" in params ||
        "viewId" in params
    ) {
        params.viewId ||= 123_456_789;
        params.searchViewId ||= 987_654_321;
        registerDefaultView(params.resModel, params.viewId, params.type, params.arch);
        registerDefaultView(params.resModel, params.searchViewId, "search", params.searchViewArch);
    }

    delete params.arch;
    delete params.config;
    delete params.searchViewArch;

    return params;
};

/**
 *
 * @param {string} modelName
 * @param {number | false} viewId
 * @param {ViewType} viewType
 * @param {string} arch
 */
const registerDefaultView = (modelName, viewId, viewType, arch) => {
    const model = MockServer.env[modelName];
    const key = model._getViewKey(viewType, viewId);
    model._views[key] ||= arch || `<${viewType} />`;
};

class ViewDialog extends Component {
    static components = { Dialog, View };

    static props = {
        viewEnv: Object,
        viewProps: Object,
    };

    static template = xml`
        <Dialog>
            <View t-props="props.viewProps" />
        </Dialog>
    `;

    setup() {
        useSubEnv(this.props.viewEnv);
    }
}

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {SelectorOptions} [options]
 */
export async function clickButton(options) {
    await contains(buildSelector(`.btn:enabled`, options)).click();
}

/**
 * @param {SelectorOptions} [options]
 */
export async function clickCancel(options) {
    await contains(buildSelector(`.o_form_button_cancel:enabled`, options)).click();
}

/**
 * @param {SelectorOptions} [options]
 */
export async function clickKanbanCard(options) {
    await contains(buildSelector(`.o_kanban_record`, options)).click();
}

/**
 * @param {SelectorOptions} [options]
 */
export async function clickModalButton(options) {
    await contains(buildSelector(`.modal .btn:enabled`, options)).click();
}

/**
 * @param {SelectorOptions} [options]
 */
export async function clickSave(options) {
    await contains(buildSelector(`.o_form_button_save:enabled`, options)).click();
}

/**
 * @param {SelectorOptions} [options]
 */
export async function clickViewButton(options) {
    await contains(buildSelector(`.o_view_controller .btn:enabled`, options)).click();
}

/**
 * @param {string} name
 * @param {SelectorOptions} options
 */
export function fieldInput(name, options) {
    return contains(buildSelector(`.o_field_widget[name='${name}'] input`, options));
}

/**
 * @param {SelectorOptions} options
 */
export function kanbanCard(options) {
    return contains(buildSelector(`.o_kanban_record`, options));
}

/**
 * @param {MountViewParams} params
 */
export async function mountViewInDialog(params) {
    const config = { ...getDefaultConfig(), ...params.config };
    const container = await mountWithCleanup(MainComponentsContainer, {
        env: params.env || getMockEnv() || (await makeMockEnv()),
    });

    getService("dialog").add(ViewDialog, {
        viewEnv: { config },
        viewProps: parseViewProps(params),
    });

    await waitFor(`.o_content`);

    return container;
}

/**
 * @param {MountViewParams} params
 */
export async function mountView(params) {
    const config = { ...getDefaultConfig(), ...params.config };
    return mountWithCleanup(View, {
        env: params.env || getMockEnv() || (await makeMockEnv({ config })),
        props: parseViewProps(params),
    });
}
