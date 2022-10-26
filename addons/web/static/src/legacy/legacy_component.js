/** @odoo-module **/

/**
 * @deprecated
 * This component SHOULD NOT be used!
 * It's used in legacy when components should work like in owl 1.
 *
 * If you need to get the component's `el` then use `useRef`
 * and if you need to send info to the component's parent then use props.
 *
 * e.g.
 * // OWL 1
 * class Component_OWL1 extends owl.Component {
 *   static template = owl.tags.xml`
 *     <button t-on-click="() => this.trigger('up')">click me</button>
 *   `;
 *   mounted() {
 *     this.el.style = "color: red";
 *   }
 * }
 *
 * // OWL 2
 * class Component_OWL2 extends owl.Component {
 *   static template = owl.xml`
 *     <button t-ref="btn" t-on-click="() => props.up()">click me</button>
 *   `;
 *   setup() {
 *     this.btnRef = useRef("btn");
 *     owl.onMounted(() => {
 *       this.btnRef.el.style = "color: red";
 *     });
 *   }
 * }
 */
export class LegacyComponent extends owl.Component {
    get el() {
        const bdom = this.__owl__.bdom;
        if (!bdom) {
            return null;
        }

        const el = (bdom.component && bdom.component.el) || bdom.firstNode();
        return el.nodeType === Node.ELEMENT_NODE ? el : null;
    }
    /**
     * Add a new method to owl Components to ensure that no performed RPC is
     * resolved/rejected when the component is destroyed.
     */
    rpc() {
        return new Promise((resolve, reject) => {
            return this.env.services
                .rpc(...arguments)
                .then((result) => {
                    if (owl.status(this) !== "destroyed") {
                        resolve(result);
                    }
                })
                .catch((reason) => {
                    if (owl.status(this) !== "destroyed") {
                        reject(reason);
                    }
                });
        });
    }

    /**
     * Emit a custom event of type 'eventType' with the given 'payload' on the
     * component's el, if it exists. However, note that the event will only bubble
     * up to the parent DOM nodes. Thus, it must be called between mounted() and
     * willUnmount().
     */
    trigger(eventType, payload) {
        this.__trigger(eventType, payload);
    }
    /**
     * Private trigger method, allows to choose the component which triggered
     * the event in the first place
     */
    __trigger(eventType, payload) {
        if (this.env[odoo.widgetSymbol]) {
            this.env[odoo.widgetSymbol](eventType);
        }
        if (this.el) {
            const ev = new CustomEvent(eventType, {
                bubbles: true,
                cancelable: true,
                detail: payload,
            });
            this.el.dispatchEvent(ev);
        }
    }
}
