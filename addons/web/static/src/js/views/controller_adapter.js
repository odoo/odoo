odoo.define('web.ControllerAdapter', function (require) {
"use strict";

var AbstractController = require('web.AbstractController');

var ControllerAdapter = AbstractController.extend({
    on_attach_callback: function () {
        this.renderer.__callMounted();
    },
    on_detach_callback: function () {
        this.renderer.__callWillUnmount();
    },

    /**
     * @override
     * */
    updateRendererState: async function (props) {
        let prom;
        this.renderer.updateProps(props);
        if (this.renderer.__owl__.isMounted) {
            prom = this.renderer.render();
        } else {
            prom = this.renderer.mount(this.$('.o_content')[0], true);
        }
        return prom;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * @override
     * @private
     */
    _startRenderer: async function () {
        return this.renderer.mount(this.$('.o_content')[0]);
    },
});

return ControllerAdapter;

});
