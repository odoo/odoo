
odoo.define('mass_mailing.fix.LinkDialog', function (require) {
'use strict';

const LinkDialog = require('wysiwyg.widgets.LinkDialog');

/**
 * Primary and link buttons are "hacked" by mailing themes scss. We thus
 * have to show them first in the link dialog, and even if they are a duplicate
 * of other colors. We also have to fix their preview if possible.
 */
LinkDialog.include({
    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this.__showDuplicateColorButtons = true;
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var ret = this._super.apply(this, arguments);

        this.opened().then(function () {
            // Ugly hack to put primary choice next to the link choice and the
            // rest on another lines (the rest are colors independent from the
            // mailing theme).
            var $mainButtons = self.$('.o_link_dialog_color_item.btn-primary');
            $mainButtons.insertAfter(self.$('.o_link_dialog_color_item.btn-link'));
            $mainButtons.before(' ');
            $mainButtons.last().after('<br/>');

            // More ugly hack to show the real color for link and primary
            // which depend on the mailing themes. Note: the hack is not enough
            // has the mailing theme changes those colors in some environment,
            // sometimes (for example 'btn-primary in this snippet looks like
            // that')... we'll consider this a limitation until a master
            // refactoring of those mailing themes.
            self.__realMMColors = {};
            var $previewArea = $('<div/>').addClass('o_mail_snippet_general');
            $(self.editable).find('.o_layout').append($previewArea);
            _.each(['link', 'primary', 'secondary'], function (type) {
                var $el = $('<a href="#" class="btn btn-' + type + '"/>');
                $el.appendTo($previewArea);
                self.__realMMColors[type] = {
                    'border-color': $el.css('border-top-color'),
                    'background-color': $el.css('background-color'),
                    'color': $el.css('color'),
                };
                $el.remove();

                self.$('.o_link_dialog_color_item.btn-' + type)
                    .css(_.pick(self.__realMMColors[type], 'background-color', 'color'));
            });
            $previewArea.remove();

            self._adaptPreview();
        });

        return ret;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _adaptPreview: function () {
        var self = this;
        this._super.apply(this, arguments);
        if (this.__realMMColors) {
            var $preview = this.$("#link-preview");
            $preview.css('border-color', '');
            $preview.css('background-color', '');
            $preview.css('color', '');
            _.each(['link', 'primary', 'secondary'], function (type) {
                if ($preview.hasClass('btn-' + type) || type === 'link' && !$preview.hasClass('btn')) {
                    $preview.css(self.__realMMColors[type]);
                }
            });
        }
    },
});

});
