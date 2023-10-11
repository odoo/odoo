/** @odoo-module **/

import {
    App,
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useEnv,
    useRef,
    useState,
    xml,
} from "@odoo/owl";
import { templates } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

const reBSTooltip = /^bs-.*$/;

export function cleanDomFromBootstrap() {
    const body = document.body;
    // multiple bodies in tests
    // Bootstrap tooltips
    const tooltips = body.querySelectorAll("body .tooltip");
    for (const tt of tooltips) {
        if (Array.from(tt.classList).find((cls) => reBSTooltip.test(cls))) {
            tt.parentNode.removeChild(tt);
        }
    }
}

export function createWidgetParent(env) {
    return {
        env,
        _trigger_up: (ev) => {
            if (ev.name === "call_service") {
                const service = env.services[ev.data.service];
                const result = service[ev.data.method].apply(service, ev.data.args || []);
                ev.data.callback(result);
            }
        },
    };
}

export function useWidget(refName, widgetClass, params = []) {
    const ref = useRef(refName);
    const env = useEnv();

    const parent = createWidgetParent(env);
    const widget = new widgetClass(parent, ...params);

    onWillStart(() => {
        return widget._widgetRenderAndInsert(() => {});
    });
    onMounted(() => {
        ref.el.append(widget.el);
    });
    onWillUnmount(() => {
        widget.destroy();
    });

    return widget;
}

const rootTemplate = xml`<SubComp t-props="state"/>`;
export async function attachComponent(parent, element, componentClass, props = {}) {
    class Root extends Component {
        static template = rootTemplate;
        static components = { SubComp: componentClass };
        state = useState(props);
    }

    const env = Component.env;
    const app = new App(Root, {
        env,
        templates,
        dev: env.debug,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
    });

    if (parent.__parentedMixin) {
        parent.__parentedChildren.push({
            get $el() {
                return $(app.root.el);
            },
            destroy() {
                app.destroy();
            },
        });
    }

    const component = await app.mount(element);
    const subComp = Object.values(component.__owl__.children)[0].component;
    return {
        component: subComp,
        destroy() {
            app.destroy();
        },
        update(props) {
            Object.assign(component.state, props);
        },
    };
}
