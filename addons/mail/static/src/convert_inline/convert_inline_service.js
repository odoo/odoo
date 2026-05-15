import { Component, onMounted, props, signal, types, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

const mainComponents = registry.category("main_components");

export class ConvertInlineContainer extends Component {
    static template = xml`<div class="o-convert-inline" t-ref="this.props.rootRef"/>`;

    setup() {
        this.props = props({
            onMounted: types.function([]),
            rootRef: types.signal(types.instanceOf(HTMLDivElement)),
        });
        onMounted(() => {
            this.props.onMounted();
        });
    }
}

export const convertInlineIframeService = {
    start() {
        const rootRef = signal.ref(HTMLDivElement);
        const { promise: readyPromise, resolve } = Promise.withResolvers();
        mainComponents.add("ConvertInlineContainer", {
            Component: ConvertInlineContainer,
            props: { onMounted: resolve, rootRef },
        });
        return {
            add: (iframe, ref) => {
                const el = ref?.();
                if (el) {
                    el.append(iframe);
                } else {
                    rootRef().append(iframe);
                }
                return () => iframe.remove();
            },
            readyPromise,
        };
    },
};

registry.category("services").add("convert_inline_iframe", convertInlineIframeService);
