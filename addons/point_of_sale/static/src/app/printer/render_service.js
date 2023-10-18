/** @odoo-module **/
/* global html2canvas */

import { registry } from "@web/core/registry";
import { Component, onRendered, reactive, useRef, xml } from "@odoo/owl";

export class RenderContainer extends Component {
    static props = ["comp", "onRendered"];
    // the `.render-container` is used by other functions that need a
    // place where to momentarily render some html code
    // we should only intact with that div through the `whenMounted` function
    static template = xml`
        <div style="left: -1000px; position: absolute;">
            <div t-ref="ref">
                <t t-if="props.comp.component" t-component="props.comp.component" t-props="props.comp.props"/>
            </div>
            <div class="render-container" />
        </div>`;
    setup() {
        this.ref = useRef("ref");
        onRendered(async () => {
            // this timeout is needed in order to wait for the
            // component to arrive in it's final state
            await new Promise((r) => setTimeout(r, 100));
            this.props.onRendered(this.ref?.el?.firstChild);
        });
    }
}
/**
 * This service does for components what renderToElement does for templates.
 * In order to obtain the html code that represents a component, we need to
 * actually mount the respective component in the dom.
 */
const renderService = {
    dependencies: [],
    start() {
        const toBeRenderedComponentData = reactive({});
        let elem, resolver;
        registry.category("main_components").add("RenderContainer", {
            Component: RenderContainer,
            props: {
                comp: toBeRenderedComponentData,
                onRendered: (el) => {
                    elem = el;
                    resolver?.();
                    // after obtaining the html code, we need to flush the
                    // contents of the RenderContainer component
                    toBeRenderedComponentData.component = null;
                },
            },
        });
        const toHtml = async (component, props) => {
            Object.assign(toBeRenderedComponentData, { component, props });
            // we wait for the RenderContainer component to actually
            // render our component
            await new Promise((r) => (resolver = r));
            return elem;
        };
        const toCanvas = async (component, props, options) => {
            return htmlToCanvas(await toHtml(component, props), options);
        };
        const toJpeg = async (component, props, options) => {
            const canvas = await toCanvas(component, props, options);
            return canvas.toDataURL("image/jpeg").replace("data:image/jpeg;base64,", "");
        };
        const whenMounted = async ({ el, container, callback }) => {
            container ||= document.querySelector(".render-container");
            return await applyWhenMounted({ el, container, callback });
        };
        return { toHtml, toCanvas, toJpeg, whenMounted };
    },
};
registry.category("services").add("renderer", renderService);

/**
 * This function is meant to be used for the cases where an
 * action needs to be performed based on some html code, but
 * that html code has to be in the dom for the action to be
 * performed. ( for example calling html2canvas )
 */
const applyWhenMounted = async ({ el, container, callback }) => {
    const elClone = el.cloneNode(true);
    container.appendChild(elClone);
    const res = await callback(elClone);
    elClone.remove();
    return res;
};

/**
 * This function assumes that the `renderer` service is available.
 */
export const htmlToCanvas = async (el, options) => {
    el.classList.add(options.addClass || "");
    // html2canvas expects the given element to be in the DOM
    return await applyWhenMounted({
        el,
        container: document.querySelector(".render-container"),
        callback: async (el) =>
            await html2canvas(el, {
                height: Math.ceil(el.clientHeight),
                width: Math.ceil(el.clientWidth),
                scale: 1,
            }),
    });
};
