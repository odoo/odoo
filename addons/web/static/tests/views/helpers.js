/** @odoo-module **/

import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, mount } from "@web/../tests/helpers/utils";
import { getDefaultConfig, View } from "@web/views/view";
import { MainComponentsContainer } from "@web/core/main_components_container";
import {
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
} from "../search/helpers";
import { addLegacyMockEnvironment } from "../webclient/helpers";
import {
    fakeCompanyService,
    makeFakeLocalizationService,
    makeFakeRouterService,
    makeFakeUserService,
} from "../helpers/mock_services";
import { commandService } from "@web/core/commands/command_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { popoverService } from "@web/core/popover/popover_service";
import { createDebugContext } from "@web/core/debug/debug_context";

import { mapLegacyEnvToWowlEnv } from "@web/legacy/utils";
import makeTestEnvironment from "web.test_env";

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
 * @returns {Component}
 */
export async function makeView(params) {
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

    if (props.arch) {
        serverData.views = serverData.views || {};
        props.viewId = params.viewId || 100000001; // hopefully will not conflict with an id already in views
        serverData.views[`${props.resModel},${props.viewId},${props.type}`] = props.arch;
        delete props.arch;
        props.searchViewId = 100000002; // hopefully will not conflict with an id already in views
        const searchViewArch = props.searchViewArch || "<search/>";
        serverData.views[`${props.resModel},${props.searchViewId},search`] = searchViewArch;
        delete props.searchViewArch;
    }

    const env = await makeTestEnv({ serverData, mockRPC });
    Object.assign(env, createDebugContext(env)); // This is needed if the views are in debug mode

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
    await addLegacyMockEnvironment(env, legacyParams);

    const target = getFixture();
    const viewEnv = Object.assign(Object.create(env), { config });
    const view = await mount(View, target, { env: viewEnv, props });
    await mount(MainComponentsContainer, target, { env, props });

    const viewNode = view.__owl__;
    const withSearchNode = Object.values(viewNode.children)[0];
    const concreteViewNode = Object.values(withSearchNode.children)[0];
    const concreteView = concreteViewNode.component;

    return concreteView;
}

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
    serviceRegistry.add("popover", popoverService), { force: true };
    serviceRegistry.add("company", fakeCompanyService);
    serviceRegistry.add("command", commandService);
}

/**
 * This helper sets the legacy env and mounts a MainComponentsContainer
 * to allow legacy code to use wowl FormViewDialogs.
 *
 * TODO: remove this when there's no legacy code using the wowl FormViewDialog.
 *
 * @param {Object} serverData
 * @param {Function} [mockRPC]
 * @returns {Promise}
 */
export async function prepareWowlFormViewDialogs(serverData, mockRPC) {
    setupViewRegistries();
    const wowlEnv = await makeTestEnv({ serverData, mockRPC });
    const legacyEnv = makeTestEnvironment();
    mapLegacyEnvToWowlEnv(legacyEnv, wowlEnv);
    owl.Component.env = legacyEnv;
    await mount(MainComponentsContainer, getFixture(), { env: wowlEnv });
}
