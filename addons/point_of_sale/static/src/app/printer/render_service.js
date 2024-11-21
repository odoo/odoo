/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onRendered, reactive, useRef, xml } from "@odoo/owl";
import { toCanvas } from "@point_of_sale/app/utils/html-to-image";

export class RenderContainer extends Component {
    static props = ["comp", "onRendered"];
    // the `.render-container` is used by other functions that need a
    // place where to momentarily render some html code
    // we should only intact with that div through the `whenMounted` function
    static template = xml`
        <div class="render-container-parent" style="left: -1000px; position: fixed;">
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
            container.innerHTML = "";
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
 * performed. ( for example calling html-to-image )
 */
const applyWhenMounted = async ({ el, container, callback }) => {
    const elClone = el.cloneNode(true);
    const sameClassElements = container.querySelectorAll(`.${[...el.classList].join(".")}`);
    // Remove all elements with the same class as the one we are about to add
    sameClassElements.forEach((element) => {
        element.remove();
    });
    container.appendChild(elClone);
    const res = await callback(elClone);
    return res;
};

/**
 * This function assumes that the `renderer` service is available.
 */
export const htmlToCanvas = async (el, options) => {
    if (options.addClass) {
        el.classList.add(...options.addClass.split(" "));
    }
    return await applyWhenMounted({
        el,
        container: document.querySelector(".render-container"),
        callback: async (el) => {
            return toCanvas(el, {
                backgroundColor: "#ffffff",
                height: Math.ceil(el.clientHeight),
                width: Math.ceil(el.clientWidth),
                pixelRatio: 1,
            });
        },
    });
};
