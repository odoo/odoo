odoo.define('web_editor.wysiwyg.root', function (require) {
'use strict';

var Widget = require('web.Widget');

var assetsLoaded = false;

var WysiwygRoot = Widget.extend({
    assetLibs: ['web_editor.compiled_assets_wysiwyg'],
    _loadLibsTplRoute: '/web_editor/public_render_template',

    publicMethods: ['isDirty', 'save', 'getValue', 'setValue', 'getEditable', 'on', 'trigger', 'focus', 'saveModifiedImages'],

    /**
     *   @see 'web_editor.wysiwyg' module
     **/
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this._params = params;
        this.$editor = null;
    },
    /**
     * Load assets
     *
     * @override
     **/
    willStart: function () {
        var self = this;

        var $target = this.$el;
        this.$el = null;

        return this._super().then(function () {
            // FIXME: this code works by pure luck. If the web_editor.wysiwyg
            // JS module was requiring a delayed module, using it here right
            // away would lead to a crash.
            if (!assetsLoaded) {
                var Wysiwyg = odoo.__DEBUG__.services['web_editor.wysiwyg'];
                _.each(['getRange', 'setRange', 'setRangeFromNode'], function (methodName) {
                    WysiwygRoot[methodName] = Wysiwyg[methodName].bind(Wysiwyg);
                });
                assetsLoaded = true;
            }

            var Wysiwyg = self._getWysiwygContructor();
            var instance = new Wysiwyg(self, self._params);
            if (self.__extraAssetsForIframe) {
                instance.__extraAssetsForIframe = self.__extraAssetsForIframe;
            }
            self._params = null;

            _.each(self.publicMethods, function (methodName) {
                self[methodName] = instance[methodName].bind(instance);
            });

            return instance.attachTo($target).then(function () {
                self.$editor = instance.$editor || instance.$el;
            });
        });
    },

    _getWysiwygContructor: function () {
        return odoo.__DEBUG__.services['web_editor.wysiwyg'];
    }
});

return WysiwygRoot;

});

odoo.define('web_editor.wysiwyg.default_options', function (require) {
'use strict';

/**
 * TODO this should be refactored to be done another way, same as the 'root'
 * module that should be done another way.
 *
 * This allows to have access to default options that are used in the summernote
 * editor so that they can be tweaked (instead of entirely replaced) when using
 * the editor on an editable content.
 */

var core = require('web.core');

var _lt = core._lt;

return {
    styleTags: ['p', 'pre', 'small', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote'],
    fontSizes: [_lt('Default'), 8, 9, 10, 11, 12, 14, 18, 24, 36, 48, 62],
};
});

// TODO should be moved in a dedicated file in newer versions
odoo.define('web_editor.browser_extensions', function (require) {
'use strict';

// Redefine the getRangeAt function in order to avoid an error appearing
// sometimes when an input element is focused on Firefox.
// The error happens because the range returned by getRangeAt is "restricted".
// Ex: Range { commonAncestorContainer: Restricted, startContainer: Restricted,
// startOffset: 0, endContainer: Restricted, endOffset: 0, collapsed: true }
// The solution consists in detecting when the range is restricted and then
// redefining it manually based on the current selection.
const originalGetRangeAt = Selection.prototype.getRangeAt;
Selection.prototype.getRangeAt = function () {
    let range = originalGetRangeAt.apply(this, arguments);
    // Check if the range is restricted
    if (range.startContainer && !Object.getPrototypeOf(range.startContainer)) {
        // Define the range manually based on the selection
        range = document.createRange();
        range.setStart(this.anchorNode, 0);
        range.setEnd(this.focusNode, 0);
    }
    return range;
};
});
