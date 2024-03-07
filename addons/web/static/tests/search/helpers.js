import { Component, xml } from "@odoo/owl";
import { findComponent, makeMockEnv, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { WithSearch } from "@web/search/with_search/with_search";
import { getDefaultConfig } from "@web/views/view";

/**
 * This function is aim to be used only in the tests.
 * It will filter the props that are needed by the Component.
 * This is to avoid errors of props validation. This occurs for example, on ControlPanel tests.
 * In production, View use WithSearch for the Controllers, and the Layout send only the props that
 * need to the ControlPanel.
 *
 * @param {Component} Component
 * @param {Object} props
 * @returns {Object} filtered props
 */
function filterPropsForComponent(Component, props) {
    // This if, can be removed once all the Components have the props defined
    if (Component.props) {
        let componentKeys = null;
        if (Component.props instanceof Array) {
            componentKeys = Component.props.map((x) => x.replace("?", ""));
        } else {
            componentKeys = Object.keys(Component.props);
        }
        if (componentKeys.includes("*")) {
            return props;
        } else {
            return Object.keys(props)
                .filter((k) => componentKeys.includes(k))
                .reduce((o, k) => {
                    o[k] = props[k];
                    return o;
                }, {});
        }
    } else {
        return props;
    }
}

/**
 * Mounts a component wrapped within a WithSearch.
 *
 * @template T
 * @param {T} componentConstructor
 * @param {Record<string, any>} [options]
 * @param {Record<string, any>} [config]
 * @returns {Promise<InstanceType<T>>}
 */
export async function mountWithSearch(componentConstructor, searchProps = {}, config = {}) {
    class ComponentWithSearch extends Component {
        static template = xml`
            <WithSearch t-props="withSearchProps" t-slot-scope="search">
                <t t-component="component" t-props="getProps(search)"/>
            </WithSearch>
        `;
        static components = { WithSearch };
        static props = ["*"];

        setup() {
            this.withSearchProps = searchProps;
            this.component = componentConstructor;
        }

        getProps(search) {
            const props = {
                context: search.context,
                domain: search.domain,
                groupBy: search.groupBy,
                orderBy: search.orderBy,
                comparison: search.comparison,
                display: search.display,
            };
            return filterPropsForComponent(componentConstructor, props);
        }
    }

    const fullConfig = { ...getDefaultConfig(), ...config };
    const env = await makeMockEnv({ config: fullConfig });
    const root = await mountWithCleanup(ComponentWithSearch, { env });
    return findComponent(root, (component) => component instanceof componentConstructor);
}
