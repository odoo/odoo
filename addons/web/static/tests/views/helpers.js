/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { View } from "@web/views/view";

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
    const props = Object.assign({}, params);
    delete props.serverData;
    delete props.mockRPC;

    const defaultFields = serverData.models[props.resModel].fields;
    if (props.arch) {
        if (!props.fields) {
            props.fields = Object.assign({}, defaultFields);
            // write the field name inside the field description (as done by fields_get)
            for (const fieldName in props.fields) {
                props.fields[fieldName].name = fieldName;
            }
        }
        props.searchViewArch = props.searchViewArch || "<search/>";
        props.searchViewFields = props.searchViewFields || Object.assign({}, props.fields);
    }

    const env = await makeTestEnv({ serverData, mockRPC });
    const target = getFixture();
    const view = await mount(View, { env, props, target });

    registerCleanup(() => view.destroy());

    const withSearch = Object.values(view.__owl__.children)[0];
    const concreteView = Object.values(withSearch.__owl__.children)[0];

    return concreteView;
}
