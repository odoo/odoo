odoo.define('web.RendererWrapper', function (require) {
    "use strict";

    const { ComponentWrapper } = require('web.OwlCompatibility');

    class RendererWrapper extends ComponentWrapper {
        get arch() {
            return this.props.arch;
        }
        getLocalState() {
            const renderer = this.componentRef.comp;
            return renderer ? renderer.getLocalState(...arguments) : undefined;
        }
        setLocalState() {
            const renderer = this.componentRef.comp;
            return renderer ? renderer.setLocalState(...arguments) : undefined;
        }
        giveFocus() {
            const renderer = this.componentRef.comp;
            return renderer ? renderer.giveFocus(...arguments) : undefined;
        }
    }

    return RendererWrapper;

});
