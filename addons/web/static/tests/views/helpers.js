/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture } from "@web/../tests/helpers/utils";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { getDefaultConfig, View } from "@web/views/view";
import { _fieldsViewGet } from "../helpers/mock_server";
import {
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
} from "../search/helpers";
import { addLegacyMockEnvironment } from "../webclient/helpers";
import {
    makeFakeLocalizationService,
    makeFakeRouterService,
    makeFakeUserService,
} from "../helpers/mock_services";
import { dialogService } from "@web/core/dialog/dialog_service";

const { mount } = owl;
const serviceRegistry = registry.category("services");

/**
 * @typedef {{
 *  serverData: Object,
 *  mockRPC?: Function,
 *  type: string,
 *  resModel: string,
 *  [prop:string]: any
 * }} MakeViewParams
 */

/**
 * @param {MakeViewParams} params
 * @returns {owl.Component}
 */
export const makeView = async (params) => {
    const props = { ...params };
    const serverData = props.serverData;
    const mockRPC = props.mockRPC;
    const config = {
        ...getDefaultConfig(),
        ...props.config,
    };
    const legacyParams = props.legacyParams || {};

    delete props.serverData;
    delete props.mockRPC;
    delete props.legacyParams;
    delete props.config;

    const env = await makeTestEnv({ serverData, mockRPC, config });

    if (props.arch) {
        const defaultFields = serverData.models[props.resModel].fields;
        if (!props.fields) {
            props.fields = Object.assign({}, defaultFields);
            // write the field name inside the field description (as done by fields_get)
            for (const fieldName in props.fields) {
                props.fields[fieldName].name = fieldName;
            }
        }
        const fvg = _fieldsViewGet({
            arch: props.arch,
            modelName: props.resModel,
            fields: props.fields,
            context: props.context || {},
            models: serverData.models,
        });
        props.arch = fvg.arch;
        props.fields = Object.assign({}, props.fields, fvg.fields);
        props.searchViewArch = props.searchViewArch || "<search/>";
        props.searchViewFields = props.searchViewFields || Object.assign({}, props.fields);
        if (props.loadActionMenus) {
            props.actionMenus = props.actionMenus === undefined ? {} : props.actionMenus;
        }
        if (props.loadIrFilters) {
            props.irFilters = props.irFilters === undefined ? [] : props.irFilters;
        }
    }

    /** Legacy Environment, for compatibility sakes
     *  Remove this as soon as we drop the legacy support
     */
    const models = params.serverData.models;
    if (legacyParams && legacyParams.withLegacyMockServer && models) {
        legacyParams.models = Object.assign({}, 0);
        // In lagacy, data may not be sole models, but can contain some other variables
        // So we filter them out for our WOWL mockServer
        Object.entries(legacyParams.models).forEach(([k, v]) => {
            if (!(v instanceof Object) || !("fields" in v)) {
                delete models[k];
            }
        });
    }
    addLegacyMockEnvironment(env, legacyParams);
    //

    const target = getFixture();
    const view = await mount(View, { env, props, target });
    const mainComponentsContainer = await mount(MainComponentsContainer, { env, props, target });

    registerCleanup(() => view.destroy());
    registerCleanup(() => mainComponentsContainer.destroy());

    const withSearch = Object.values(view.__owl__.children)[0];
    const concreteView = Object.values(withSearch.__owl__.children)[0];

    return concreteView;
};

export function setupViewRegistries() {
    setupControlPanelFavoriteMenuRegistry();
    setupControlPanelServiceRegistry();
    serviceRegistry.add(
        "user",
        makeFakeUserService((group) => group === "base.group_allow_export"),
        { force: true }
    );
    serviceRegistry.add("router", makeFakeRouterService(), { force: true });
    serviceRegistry.add("localization", makeFakeLocalizationService()), { force: true };
    serviceRegistry.add("dialog", dialogService), { force: true };
}
