odoo.define('website.settings', function (require) {

var BaseSettingController = require('base.settings').Controller;
var FormController = require('web.FormController');

BaseSettingController.include({

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Bypasses the discard confirmation dialog when going to a website because
     * the target website will be the one selected.
     *
     * Without this override, it is impossible to go to a website other than the
     * first because discarding will revert it back to the default value.
     *
     * @override
     */
    _onButtonClicked: function (ev) {
        if (ev.data.attrs.name === 'website_go_to') {
            FormController.prototype._onButtonClicked.apply(this, arguments);
        } else {
            this._super.apply(this, arguments);
        }
    },
});
});
