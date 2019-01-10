odoo.define('web_editor.wysiwyg.plugin.transform', function (require) {
'use strict';

var core = require('web.core');
var AbstractPlugin = require('web_editor.wysiwyg.plugin.abstract');
var registry = require('web_editor.wysiwyg.plugin.registry');
var wysiwygTranslation = require('web_editor.wysiwyg.translation');
var wysiwygOptions = require('web_editor.wysiwyg.options');

var _t = core._t;


var TransformPlugin = AbstractPlugin.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Manages transformations on a media.
     */
    transform: function () {
        var $image = $(this.context.invoke('editor.restoreTarget'));

        if ($image.data('transfo-destroy')) {
            $image.removeData('transfo-destroy');
            return;
        }

        $image.transfo(); // see web_editor/static/lib/jQuery.transfo.js

        var mouseup = function () {
            $('.note-popover button[data-event="transform"]').toggleClass('active', $image.is('[style*="transform"]'));
        };
        $(document).on('mouseup', mouseup);

        var mousedown = this._wrapCommand(function (event) {
            if (!$(event.target).closest('.transfo-container').length) {
                $image.transfo('destroy');
                $(document).off('mousedown', mousedown).off('mouseup', mouseup);
            }
            if ($(event.target).closest('.note-popover').length) {
                var transformStyles = self.context.invoke('HelperPlugin.getRegex', '', 'g', '[^;]*transform[\\w:]*;?');
                $image.data('transfo-destroy', true).attr('style', ($image.attr('style') || '').replace(transformStyles, ''));
            }
        });
        $(document).on('mousedown', mousedown);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds the transform buttons.
     *
     * @override
     */
    _addButtons: function () {
        var self = this;
        this._super();

        this.context.memo('button.transform', function () {
            return self.context.invoke('buttons.button', {
                contents: self.ui.icon(self.options.icons.transform),
                tooltip: self.lang.image.transform,
                click: self.context.createInvokeHandler('TransformPlugin.transform'),
            }).render();
        });
    },

});


_.extend(wysiwygOptions.icons, {
    transform: 'fa fa-object-ungroup',
});
_.extend(wysiwygTranslation.image, {
    transform: _t('Transform the picture (click twice to reset transformation)'),
});

registry.add('TransformPlugin', TransformPlugin);

return TransformPlugin;

});
