/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { View } from "@web/views/view";
import { _fieldsViewGet } from "../helpers/mock_server";
import { addLegacyMockEnvironment } from "../webclient/helpers";

const { mount } = owl;

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
export async function makeView(params) {
    const serverData = params.serverData;
    const mockRPC = params.mockRPC;
    const legacyParams = params.legacyParams || {};
    const props = Object.assign({}, params);
    delete props.serverData;
    delete props.mockRPC;
    delete props.legacyParams;

    const env = await makeTestEnv({ serverData, mockRPC });
    const defaultFields = serverData.models[props.resModel].fields;
    if (props.arch) {
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
    const view = await mount(View, { env, props, target });

    registerCleanup(() => view.destroy());

    const withSearch = Object.values(view.__owl__.children)[0];
    const concreteView = Object.values(withSearch.__owl__.children)[0];

    return concreteView;
}
