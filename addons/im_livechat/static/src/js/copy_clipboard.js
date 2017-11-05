odoo.define('im_livechat.copy_clipboard', function (require) {
"use strict";

var core = require('web.core');
var field_registry = require('web.field_registry');
var qweb = core.qweb;

var _t = core._t;
var FieldText = field_registry.get('text');
var FieldChar = field_registry.get('char');

var CopyClipboard = {

    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.clipboard.destroy();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instatiates the Clipboad lib.
     */
    _initClipboard: function () {
        var self = this;
        var $clipboardBtn = this.$('.o_clipboard_button');
        $clipboardBtn.tooltip({title: _t('Copied !'), trigger: 'manual', placement: 'right'});
        this.clipboard = new Clipboard($clipboardBtn.get(0), {
            text: function () {
                return self.value.trim();
            }
        });
        this.clipboard.on('success', function () {
            _.defer(function () {
                $clipboardBtn.tooltip('show');
                _.delay(function () {
                    $clipboardBtn.tooltip('hide');
                }, 800);
            });
        });
    },
};

var TextCopyClipboard = FieldText.extend(CopyClipboard, {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _render: function() {
        this._super.apply(this, arguments);
        this.$el.addClass('o_field_copy');
        this.$el.append($(qweb.render('CopyClipboardText')));
        this._initClipboard();
    }
});

var CharCopyClipboard = FieldChar.extend(CopyClipboard, {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _render: function() {
        this._super.apply(this, arguments);
        this.$el.addClass('o_field_copy');
        this.$el.append($(qweb.render('CopyClipboardChar')));
        this._initClipboard();
    }
});

field_registry
    .add('CopyClipboardText', TextCopyClipboard)
    .add('CopyClipboardChar', CharCopyClipboard);
});
