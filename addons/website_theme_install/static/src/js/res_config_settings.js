odoo.define('website_theme_install.settings', function (require) {

var BaseSettingController = require('base.settings').Controller;
var FormController = require('web.FormController');

BaseSettingController.include({

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Bypasses the discard confirmation dialog when selecting a theme because
     * the theme will be installed on the selected website.
     *
     * Without this override, it is impossible to install a theme on a website
     * other than the first because discarding will revert it back to the
     * default value.
     *
     * @override
     */
    _onButtonClicked: function (ev) {
        if (ev.data.attrs.name === 'install_theme_on_current_website') {
            FormController.prototype._onButtonClicked.apply(this, arguments);
        } else {
            this._super.apply(this, arguments);
        }
    },
});
});
