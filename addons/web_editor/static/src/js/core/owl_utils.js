import { App, Component, useState, xml } from "@odoo/owl";
import { getTemplate } from "@web/core/templates";
import { appTranslateFn } from "@web/core/l10n/translation";

const rootTemplate = xml`<SubComp t-props="state"/>`;
export async function attachComponent(parent, element, componentClass, props = {}) {
    class Root extends Component {
        static template = rootTemplate;
        static components = { SubComp: componentClass };
        static props = ["*"];
        state = useState(props);
    }

    const env = Component.env;
    const app = new App(Root, {
        env,
        getTemplate,
        dev: env.debug,
        translatableAttributes: ["data-tooltip"],
        translateFn: appTranslateFn,
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

    const originalValidateTarget = App.validateTarget;
    App.validateTarget = () => {};
    const mountPromise = app.mount(element);
    App.validateTarget = originalValidateTarget;
    const component = await mountPromise;
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
