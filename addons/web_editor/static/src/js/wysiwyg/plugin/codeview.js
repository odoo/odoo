odoo.define('web_editor.wysiwyg.plugin.codeview', function (require) {
'use strict';

var core = require('web.core');
var Plugins = require('web_editor.wysiwyg.plugins');
var registry = require('web_editor.wysiwyg.plugin.registry');

var _t = core._t;


var CodeviewPlugin = Plugins.codeview.extend({
    /**
     * @override
     */
    activate: function () {
        this._super();
        if (this.$codable.height() === 0) {
            this.$codable.height(180);
        }
        this.context.invoke('editor.hidePopover');
        this.context.invoke('editor.clearTarget');
    },
    /**
     * @override
     */
    deactivate: function () {
        if (
            this.context.invoke('HelperPlugin.hasJinja', this.context.invoke('code')) &&
            !this.isBeingDestroyed
        ) {
            var message = _t("Your code contains JINJA conditions.\nRemove them to return to WYSIWYG HTML edition.");
            this.do_warn(_t("Cannot edit HTML"), message);
            this.$codable.focus();
            return;
        }
        this._super();
        this.$editable.css('height', '');
    },
    /**
     * @override
     */
    destroy: function () {
        this.isBeingDestroyed = true;
        this._super();
    },
    /**
     * Force activation of the code view.
     */
    forceActivate: function () {
        if (!this.isActivated()) {
            this.activate();
        }
    },
});

registry.add('codeview', CodeviewPlugin);

return CodeviewPlugin;

});
