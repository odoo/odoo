odoo.define('web.RendererWrapper', function (require) {
    "use strict";

    const { xml } = owl.tags;
    const AbstractRenderer = require('web.AbstractRendererOwl');

    class RendererWrapper extends owl.Component {
        /**
         *
         * @param {Object} parent
         * @param {Object} props
         * @param {Class} concreteRenderer
         */
        constructor(parent, props, concreteRenderer) {
            super(...arguments);
            this.concreteRenderer = concreteRenderer;
            this.data = props;
        }

        /**
         * Update the props of the renderer before a re-render
         * called on the initial render as well as when the renderer is re-mounted (view switched)
         *
         * @param {Object} props new props
         */
        updateProps(props) {
            this.data = Object.assign(this.data || {}, props);
        }

        mounted() {
            for (let x in this.__owl__.children) {
                this.__owl__.children[x].__callMounted();
            }
        }

        willUnmount() {
            for (let x in this.__owl__.children) {
                this.__owl__.children[x].__callWillUnmount();
            }
        }

        setParent() { }

        getLocalState() { }

        setLocalState() { }

        giveFocus() { }
    };

    RendererWrapper.template = xml`<t t-component="concreteRenderer" t-props="data"/>`;

    RendererWrapper.components = { AbstractRenderer };

    return RendererWrapper;

});
