import { after, expect, getFixture } from "@odoo/hoot";
import { click, formatXml, queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame, Deferred, tick } from "@odoo/hoot-mock";
import { Component, onMounted, useSubEnv, xml } from "@odoo/owl";
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
 *  resId?: number;
 *  resModel: string;
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
 * @typedef {import("@odoo/hoot-dom").FormatXmlOptions} FormatXmlOptions
 * @typedef {import("./mock_server/mock_model").ViewType} ViewType
 */

//-----------------------------------------------------------------------------
// Internals
//-----------------------------------------------------------------------------

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
        onMounted: Function,
        viewEnv: Object,
        viewProps: Object,
        close: Function,
    };

    static template = xml`
        <Dialog>
            <View t-props="props.viewProps" />
        </Dialog>
    `;

    setup() {
        useSubEnv(this.props.viewEnv);
        onMounted(() => this.props.onMounted());
    }
}

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 *
 * @param {string} base
 * @param {SelectorOptions} [params]
 */
export function buildSelector(base, params) {
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
    if ("index" in params) {
        selector += `:eq(${params.index})`;
    }
    if (params.target) {
        selector += ` ${params.target}`;
    }
    return selector;
}

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
 * @param {string} fieldName
 * @param {SelectorOptions} [options]
 */
export async function clickFieldDropdown(fieldName, options) {
    await contains(buildSelector(`[name='${fieldName}'] .dropdown input`, options)).click();
}

/**
 * @param {string} fieldName
 * @param {string} itemContent
 * @param {SelectorOptions} [options]
 */
export async function clickFieldDropdownItem(fieldName, itemContent, options) {
    const dropdowns = queryAll(
        buildSelector(`[name='${fieldName}'] .dropdown .dropdown-menu`, options)
    );
    if (dropdowns.length === 0) {
        throw new Error(`No dropdown found for field ${fieldName}`);
    } else if (dropdowns.length > 1) {
        throw new Error(`Found ${dropdowns.length} dropdowns for field ${fieldName}`);
    }
    const dropdownItems = queryAll(buildSelector("li", options), { root: dropdowns[0] });
    const indexToClick = queryAllTexts(dropdownItems).indexOf(itemContent);
    if (indexToClick === -1) {
        throw new Error(`The element '${itemContent}' does not exist in the dropdown`);
    }
    await click(dropdownItems[indexToClick]);
    await animationFrame();
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
 * @param {string} value
 */
export function expectMarkup(value) {
    return {
        /**
         * @param {string} expected
         * @param {FormatXmlOptions} [options]
         */
        toBe(expected, options) {
            expect(formatXml(value, options)).toBe(formatXml(expected, options));
        },
    };
}

/**
 * @param {string} name
 * @param {SelectorOptions} options
 */
export function fieldInput(name, options) {
    return contains(buildSelector(`.o_field_widget[name='${name}'] input`, options));
}

/**
 * @param {MountViewParams} params
 */
export async function mountViewInDialog(params) {
    const config = { ...getDefaultConfig(), ...params.config };
    const container = await mountWithCleanup(MainComponentsContainer, {
        env: params.env || getMockEnv() || (await makeMockEnv()),
    });

    const deferred = new Deferred();
    getService("dialog").add(ViewDialog, {
        viewEnv: { config },
        viewProps: parseViewProps(params),
        onMounted() {
            deferred.resolve();
        },
    });

    await deferred;
    return container;
}

/**
 * @param {MountViewParams} params
 * @param {HTMLElement} [target]
 */
export async function mountView(params, target = null) {
    const actionManagerEl = document.createElement("div");
    actionManagerEl.classList.add("o_action_manager");
    (target ?? getFixture()).append(actionManagerEl);
    after(() => actionManagerEl.remove());
    const config = { ...getDefaultConfig(), ...params.config };
    return mountWithCleanup(View, {
        env: params.env || getMockEnv() || (await makeMockEnv({ config })),
        props: parseViewProps(params),
        target: actionManagerEl,
    });
}

/**
 * @param {MountViewParams} params
 * @returns {typeof View.props}
 */
export function parseViewProps(params) {
    let className = "o_action";
    if (params.className) {
        className += " " + params.className;
    }

    const viewProps = { ...params, className };

    // View & search view arch
    if (
        "arch" in params ||
        "searchViewArch" in params ||
        "searchViewId" in params ||
        "viewId" in params
    ) {
        viewProps.viewId ||= 123_456_789;
        viewProps.searchViewId ||= 987_654_321;
        registerDefaultView(viewProps.resModel, viewProps.viewId, viewProps.type, viewProps.arch);
        registerDefaultView(
            viewProps.resModel,
            viewProps.searchViewId,
            "search",
            viewProps.searchViewArch
        );
    }

    delete viewProps.arch;
    delete viewProps.config;
    delete viewProps.searchViewArch;

    return viewProps;
}

/**
 * Open a field dropdown and click on the item which matches the
 * given content
 * @param {string} fieldName
 * @param {string} itemContent
 * @param {SelectorOptions} [options]
 */
export async function selectFieldDropdownItem(fieldName, itemContent, options) {
    await clickFieldDropdown(fieldName, options);
    await clickFieldDropdownItem(fieldName, itemContent);
}

/**
 * Emulates the behaviour when we hide the tab in the browser.
 */
export async function hideTab() {
    const prop = Object.getOwnPropertyDescriptor(Document.prototype, "visibilityState");
    Object.defineProperty(document, "visibilityState", {
        value: "hidden",
        configurable: true,
        writable: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));
    await tick();
    Object.defineProperty(document, "visibilityState", prop);
}
