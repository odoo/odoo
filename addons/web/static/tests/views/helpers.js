/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { View } from "@web/views/view";

const { mount } = owl;

/**
 * @param {Object} params
 * @param {Object} params.serverData
 * @param {Function} [params.mockRPC]
 * @param {string} params.type
 * @param {string} params.resModel
 * @param {Component}
 */
export async function makeView(params) {
    const serverData = params.serverData;
    const mockRPC = params.mockRPC;
    const env = await makeTestEnv({ serverData, mockRPC });

    const props = Object.assign({}, params);
    delete props.serverData;
    delete props.mockRPC;
    props.fields = props.fields || serverData.models[props.resModel].fields;

    const target = getFixture();

    const view = await mount(View, { env, props, target });

    registerCleanup(() => view.destroy());

    const withSearch = Object.values(view.__owl__.children)[0];
    const concreteView = Object.values(withSearch.__owl__.children)[0];

    return concreteView;
}
