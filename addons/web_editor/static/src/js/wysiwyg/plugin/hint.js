odoo.define('web_editor.wysiwyg.plugin.hint', function (require) {
'use strict';

var Plugins = require('web_editor.wysiwyg.plugins');
var registry = require('web_editor.wysiwyg.plugin.registry');

var dom = $.summernote.dom;


var HintPlugin = Plugins.hintPopover.extend({
    init: function (context) {
        context.options.hint = (context.options.hint || []).concat(this._hints());
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public summernote module API
    //--------------------------------------------------------------------------

    /**
     * Replace the current hint.
     */
    replace: function () {
        var self = this;
        var $item = this.$content.find('.note-hint-item.active');
        if ($item.length) {
            this.lastWordRange.select();
            this.context.invoke('HelperPlugin.deleteSelection');
            var range = this.context.invoke('editor.createRange');

            this.nodeFromItem($item).each(function () {
                $(range.sc).after(this);
                range = self.context.invoke('editor.setRange', this, dom.nodeLength(this));
            });
            range.select();
            this.context.invoke('editor.saveRange');
            this.lastWordRange = null;
            this.hide();
            this.context.triggerEvent('change', this.$editable.html(), this.$editable[0]);
            this.context.invoke('editor.focus');
        }
    },
    /**
     * @param {JQueryEvent} e
     */
    handleKeyup: function (e) {
        var self = this;
        if ([13, 38, 40].indexOf(e.keyCode) === -1) { // enter, up, down
            var wordRange = this.context.invoke('editor.createRange');
            var keyword_1 = wordRange.sc.textContent.slice(0, wordRange.so);
            if (this.hints.length && keyword_1) {
                this.$content.empty();
                this.$popover.hide();
                this.lastWordRange = wordRange;
                var hasMatch = false;

                // test all hints
                this.hints.forEach(function (hint, idx) {
                    var match = keyword_1.match(hint.match);
                    if (match) {
                        hasMatch = true;
                        wordRange.so = wordRange.eo - match[0].length;
                        self.createGroup(idx, match[0]).appendTo(self.$content);
                    }
                });
                if (!hasMatch) {
                    return;
                }

                // select first .note-hint-item
                this.$content.find('.note-hint-item:first').addClass('active');

                // set position for popover after group is created
                var rect = wordRange.getClientRects()[0];
                var bnd = {
                    top: rect.top + $(this.document).scrollTop(),
                    left: rect.left + $(this.document).scrollLeft(),
                };
                this.$popover.css({
                    left: bnd.left,
                    top: bnd.top + (this.direction === 'top' ? -this.$popover.outerHeight() : (rect.bottom - rect.top)) - 5,
                });
            } else {
                this.hide();
            }
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get hint objects.
     *
     * @private
     * @returns {Object[]} hints
     */
    _hints: function () {
        var self = this;
        return [{
                className: 'o_hint_partner',
                match: /\B@(\w+(\s\w*)?)$/,
                search: function (keyword, callback) {
                    self._rpc({
                        model: 'res.partner',
                        method: "search_read",
                        fields: ['id', 'name', 'email'],
                        domain: [
                            ['name', 'ilike', keyword],
                        ],
                        limit: 10,
                    }).then(callback);
                },
                template: function (partner) {
                    return partner.name + (partner.email ? ' <i style="color: #999;">(' + partner.email + ')</i>' : '');
                },
                content: function (item) {
                    return $(self.document.createTextNode('@' + item.name + '\u00A0'));
                },
            },
            {
                className: 'fa',
                match: /:([\-+\w]+)$/,
                search: function () {},
                template: function () {
                    return '<span class="fa fa-star">\u200B</span>';
                },
                content: function () {}
            },
        ];
    },
});

registry.add('hintPopover', null);

return HintPlugin;

});
