odoo.define('base_setup.ResConfigDevTool', function (require) {
    "use strict";

    var config = require('web.config');
    var Widget = require('web.Widget');
    var widget_registry = require('web.widget_registry');

    var ResConfigDevTool = Widget.extend({
        template: 'res_config_dev_tool',
        events: {
            'click .o_web_settings_force_demo': '_onClickForceDemo',
        },

        init: function () {
            this._super.apply(this, arguments);
            this.isDebug = config.isDebug();
            this.isAssets = config.isDebug("assets");
            this.isTests = config.isDebug("tests");
        },

        willStart: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                return self._rpc({
                    route: '/base_setup/demo_active',
                }).then(function (demo_active) {
                    self.demo_active = demo_active;
                });
            });
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Forces demo data to be installed in a database without demo data installed.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickForceDemo: function (ev) {
            ev.preventDefault();
            this.do_action('base.demo_force_install_action');
        },
    });

    widget_registry.add('res_config_dev_tool', ResConfigDevTool);
});
