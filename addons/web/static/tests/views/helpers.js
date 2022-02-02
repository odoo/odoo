/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture } from "@web/../tests/helpers/utils";
import { renderToString } from "@web/core/utils/render";
import { getDefaultConfig, View } from "@web/views/view";
import { _fieldsViewGet } from "../helpers/mock_server";
import { addLegacyMockEnvironment } from "../webclient/helpers";

const { App } = owl;

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

    const app = new App(View, {
        env,
        dev: env.debug,
        props,
        templates: window.__ODOO_TEMPLATES__,
    });

    renderToString.app = app;
    const view = await app.mount(target);

    registerCleanup(() => app.destroy());

    const viewNode = view.__owl__;
    const withSearchNode = Object.values(viewNode.children)[0];
    const concreteViewNode = Object.values(withSearchNode.children)[0];
    const concreteView = concreteViewNode.component;
    //

    return concreteView;
};
