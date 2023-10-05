/** @odoo-module **/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, mount, nextTick } from "@web/../tests/helpers/utils";
import { createDebugContext } from "@web/core/debug/debug_context";
import { Dialog } from "@web/core/dialog/dialog";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { View, getDefaultConfig } from "@web/views/view";
import {
    fakeCompanyService,
    makeFakeLocalizationService,
    makeFakeRouterService,
    makeFakeUserService,
} from "../helpers/mock_services";
import {
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
} from "../search/helpers";

import { Component, useSubEnv, xml } from "@odoo/owl";

import { mapLegacyEnvToWowlEnv } from "@web/legacy/utils";
import makeTestEnvironment from "@web/../tests/legacy/helpers/test_env";

const serviceRegistry = registry.category("services");

const rootDialogTemplate = xml`<Dialog><View t-props="props.viewProps"/></Dialog>`;

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
 * @template {Component} T
 * @param {MakeViewParams} params
 * @param {boolean} [inDialog=false]
 * @returns {Promise<T>}
 */
async function _makeView(params, inDialog = false) {
    const props = { ...params };
    const serverData = props.serverData;
    const mockRPC = props.mockRPC;
    const config = {
        ...getDefaultConfig(),
        ...props.config,
    };

    delete props.serverData;
    delete props.mockRPC;
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

    const target = getFixture();
    const viewEnv = Object.assign(Object.create(env), { config });

    await mount(MainComponentsContainer, target, { env });
    let viewNode;
    if (inDialog) {
        let root;
        class RootDialog extends Component {
            setup() {
                root = this;
                useSubEnv(viewEnv);
            }
        }
        RootDialog.components = { Dialog, View };
        RootDialog.template = rootDialogTemplate;
        env.services.dialog.add(RootDialog, { viewProps: props });
        await nextTick();
        const rootNode = root.__owl__;
        const dialogNode = Object.values(rootNode.children)[0];
        viewNode = Object.values(dialogNode.children)[0];
    } else {
        const view = await mount(View, target, { env: viewEnv, props });
        await nextTick();
        viewNode = view.__owl__;
    }
    const withSearchNode = Object.values(viewNode.children)[0];
    const concreteViewNode = Object.values(withSearchNode.children)[0];
    const concreteView = concreteViewNode.component;

    return concreteView;
}

/**
 * @param {MakeViewParams} params
 */
export function makeView(params) {
    return _makeView(params);
}

/**
 * @param {MakeViewParams} params
 */
export function makeViewInDialog(params) {
    return _makeView(params, true);
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
    serviceRegistry.add("localization", makeFakeLocalizationService());
    serviceRegistry.add("company", fakeCompanyService);
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
    Component.env = legacyEnv;
    await mount(MainComponentsContainer, getFixture(), { env: wowlEnv });
}
