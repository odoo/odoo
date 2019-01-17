odoo.define('web_editor.wysiwyg.plugin.buttons', function (require) {
'use strict';

var Plugins = require('web_editor.wysiwyg.plugins');

var dom = $.summernote.dom;

Plugins.buttons.include({
    /**
     * Fix tooltip for 'option' buttons (summernote 0.8.9 bug)
     * Remove this once the library is updated to 0.8.10.
     *
     * @override
     */
    addToolbarButtons: function () {
        this.options.codeview = this.lang.options.codeview;
        this.options.help = this.lang.options.help;
        this.options.fullscreen = this.lang.options.fullscreen;
        this._super();
    },
    /**
     * Show current style (of start of selection) in magic wand dropdown.
     *
     * @param {JQuery Object} $container
     */
    updateActiveStyleDropdown: function ($container) {
        var self = this;
        var range = this.context.invoke('editor.createRange');
        var el = dom.ancestor(range.sc, function (n) {
            return n.tagName && self.options.styleTags.indexOf(n.tagName.toLowerCase()) !== -1;
        });
        if (el) {
            var tagName = el.tagName.toLowerCase();
            $container.find('.dropdown-style a').each(function (idx, item) {
                var $item = $(item);
                // always compare string to avoid creating another func.
                var isChecked = ($item.data('value') + '') === (tagName + '');
                $item.toggleClass('active', isChecked);
            });
        } else {
            var $item = $container.find('.dropdown-style a.active');
            $item.removeClass('active');
        }
    },
    /**
     * @override
     */
    updateCurrentStyle: function ($container) {
        this._super.apply(this, arguments);

        this.updateParaAlignIcon($container || this.$toolbar);
        this.updateActiveStyleDropdown($container || this.$toolbar);
    },
    /**
     * Show current paragraph alignment (of start of selection) on paragraph alignment dropdown.
     *
     * @param {JQuery Object} $container
     */
    updateParaAlignIcon: function ($container) {
        var range = this.context.invoke('editor.createRange');
        var $paraIcon = $container.find('.note-para .dropdown-toggle i');
        var el = dom.isText(range.sc) ? range.sc.parentNode : range.sc;
        if (el) {
            $paraIcon.removeClass();
            switch ($(el).css('text-align')) {
                case 'left':
                    $paraIcon.addClass('note-icon-align-left');
                    break;
                case 'center':
                    $paraIcon.addClass('note-icon-align-center');
                    break;
                case 'right':
                    $paraIcon.addClass('note-icon-align-right');
                    break;
                case 'justify':
                    $paraIcon.addClass('note-icon-align-justify');
                    break;
                default:
                    $paraIcon.addClass('note-icon-align-left');
                    break;
            }
        }
    },
});

return Plugins.buttons;

});
