odoo.define('web_editor.wysiwyg.plugin.font.buttons', function (require) {
'use strict';

var ButtonsPlugin = require('web_editor.wysiwyg.plugin.buttons');

//--------------------------------------------------------------------------
// override the ColorPicker button into the Toolbar and the font size button
//--------------------------------------------------------------------------

ButtonsPlugin.include({
    /**
     * @override
     */
    addToolbarButtons: function () {
        var self = this;
        this._super();

        this.context.memo('button.colorpicker', function () {
            return self.context.invoke('FontPlugin.createColorPickerButtons');
        });

        var fontsizeFunction = this.context.memo('button.fontsize');
        this.context.memo('button.fontsize', function () {
            return self.context.invoke('FontPlugin.overrideFontSizeButton', fontsizeFunction());
        });
    },
});

return ButtonsPlugin;

});
