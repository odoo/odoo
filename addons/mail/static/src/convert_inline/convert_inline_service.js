import { Component, onMounted, signal, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

const mainComponents = registry.category("main_components");

export class ConvertInlineContainer extends Component {
    static template = xml`<div class="o-convert-inline" t-ref="this.root"></div>`;
    static props = { share: Object };

    setup() {
        this.root = signal();
        Object.assign(this.props.share, {
            root: this.root,
        });
        onMounted(() => {
            this.props.share.resolve();
        });
    }
}

export const convertInlineIframeService = {
    start() {
        const { promise, resolve } = Promise.withResolvers();
        const share = {
            readyPromise: promise,
            resolve,
        };

        mainComponents.add("ConvertInlineContainer", {
            Component: ConvertInlineContainer,
            props: { share },
        });

        const add = (iframe) => {
            share.root().append(iframe);
            return () => iframe.remove();
        };

        return { add, readyPromise: promise };
    },
};

registry.category("services").add("convert_inline_iframe", convertInlineIframeService);
