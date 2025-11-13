import {
    after,
    animationFrame,
    click,
    Deferred,
    expect,
    formatXml,
    getFixture,
    queryAll,
    queryAllTexts,
    queryFirst,
    runAllTimers,
    tick,
} from "@odoo/hoot";
import { Component, onMounted, useSubEnv, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { View } from "@web/views/view";
import { mountWithCleanup } from "./component_test_helpers";
import { contains } from "./dom_test_helpers";
import { getMockEnv, getService } from "./env_test_helpers";
import { registerInlineViewArchs } from "./mock_server/mock_model";

/**
 * @typedef {import("@web/views/view").Config} Config
 *
 * @typedef {{
 *  value?: string;
 *  index?: number;
 * }} EditSelectMenuParams
 *
 * @typedef {ViewProps & {
 *  archs?: Record<string, string>
 *  config?: Config;
 *  env?: import("@web/env").OdooEnv;
 *  resId?: number;
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
 * @typedef {import("@odoo/hoot").FormatXmlOptions} FormatXmlOptions
 * @typedef {import("@web/views/view").ViewProps} ViewProps
 * @typedef {import("./mock_server/mock_model").ViewType} ViewType
 */

//-----------------------------------------------------------------------------
// Internals
//-----------------------------------------------------------------------------

/**
 * FIXME: isolate to external helper in @web?
 *
 * @param {unknown} value
 */
const isNil = (value) => value === null || value === undefined;

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
    if (!isNil(params.index)) {
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
    const selector = getMockEnv().isSmall
        ? `[name='${fieldName}'] input`
        : `[name='${fieldName}'] .dropdown input`;
    await contains(buildSelector(selector, options)).click();
}

/**
 * @param {string} fieldName
 * @param {string} itemContent
 * @param {SelectorOptions} [options]
 */
export async function clickFieldDropdownItem(fieldName, itemContent, options) {
    if (getMockEnv().isSmall) {
        await contains(`.o_kanban_record:contains('${itemContent}')`).click();
        return;
    }
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
    const container = await mountWithCleanup(MainComponentsContainer, {
        env: params.env,
    });
    const deferred = new Deferred();
    getService("dialog").add(ViewDialog, {
        viewEnv: { config: params.config },
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
    return mountWithCleanup(View, {
        env: params.env,
        componentEnv: { config: params.config },
        props: parseViewProps(params),
        target: actionManagerEl,
    });
}

/**
 * @param {ViewProps & { archs?: Record<string, string> }} props
 * @returns {ViewProps}
 */
export function parseViewProps(props) {
    let className = "o_action";
    if (props.className) {
        className += " " + props.className;
    }

    const viewProps = { ...props, className };

    if (
        props.archs ||
        !isNil(props.arch) ||
        !isNil(props.searchViewArch) ||
        !isNil(props.searchViewId) ||
        !isNil(props.viewId)
    ) {
        viewProps.viewId ??= -1;
        viewProps.searchViewId ??= -1;
        registerInlineViewArchs(viewProps.resModel, {
            ...props.archs,
            [[viewProps.type, viewProps.viewId]]: viewProps.arch,
            [["search", viewProps.searchViewId]]: viewProps.searchViewArch,
        });
    } else {
        // Force `get_views` call
        viewProps.viewId = false;
        viewProps.searchViewId = false;
    }

    delete viewProps.arch;
    delete viewProps.archs;
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

/**
 * Changes or clears the value in a SelectMenu component, supporting when
 * the input is displayed in the toggler, in a Dropdown menu or in a
 * BottomSheet as well. The helper can directly select a value if it's
 * displayed or perform a search in the SelectMenu input if present.
 * @param {string} selector
 * @param {EditSelectMenuParams} [params]
 */
export async function editSelectMenu(selector, { value, index }) {
    async function selectItem(value) {
        const elementToSelect = queryFirst(`.o_select_menu_item:contains(${value})`);
        if (elementToSelect) {
            await click(elementToSelect);
            return;
        } else {
            await contains(inputSelector).edit(value, { confirm: false });
            await runAllTimers();
            return selectItem(value);
        }
    }
    let inputSelector = buildSelector(selector);
    const selectMenuId = queryFirst(inputSelector).closest(".o_select_menu").dataset.id;
    if (!queryFirst(`.o_select_menu_menu [data-id='${selectMenuId}']`)) {
        await contains(inputSelector).click();
    }
    if (queryFirst(".o_select_menu_menu input")) {
        inputSelector = ".o_select_menu_menu input";
        await contains(inputSelector).click();
    }
    if (index !== undefined) {
        return await contains(`.o_select_menu_item:nth-of-type(${index + 1})`).click();
    }
    if (value === "") {
        // Because this helper must work even when no input is editable (searchable=false),
        // we unselect the currently selected value with the 'X' button
        const clearButton = queryFirst(
            `.o_select_menu[data-id='${selectMenuId}'] .o_select_menu_toggler_clear, .o_select_menu_menu .o_clear_button`
        );
        if (clearButton) {
            await click(clearButton);
        } else {
            await contains(inputSelector).edit("", { confirm: false });
            queryFirst(inputSelector).dispatchEvent(new Event("blur"));
        }
    } else {
        await selectItem(value);
    }
    await animationFrame();
}
