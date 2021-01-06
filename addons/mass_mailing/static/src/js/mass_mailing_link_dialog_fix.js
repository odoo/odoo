
odoo.define('mass_mailing.fix.LinkDialog', function (require) {
'use strict';

const LinkDialog = require('wysiwyg.widgets.LinkDialog');

/**
 * Primary and link buttons are "hacked" by mailing themes scss. We thus
 * have to fix their preview if possible.
 */
LinkDialog.include({
    /**
     * @override
     */
    start() {
        const ret = this._super(...arguments);
        if (!$(this.editable).find('.o_mail_wrapper').length) {
            return ret;
        }

        this.opened().then(() => {
            // Ugly hack to show the real color for link and primary which
            // depend on the mailing themes. Note: the hack is not enough as
            // the mailing theme changes those colors in some environment,
            // sometimes (for example 'btn-primary in this snippet looks like
            // that')... we'll consider this a limitation until a master
            // refactoring of those mailing themes.
            this.__realMMColors = {};
            const $previewArea = $('<div/>').addClass('o_mail_snippet_general');
            $(this.editable).find('.o_layout').append($previewArea);
            _.each(['link', 'primary', 'secondary'], type => {
                const $el = $('<a href="#" class="btn btn-' + type + '"/>');
                $el.appendTo($previewArea);
                this.__realMMColors[type] = {
                    'border-color': $el.css('border-top-color'),
                    'background-color': $el.css('background-color'),
                    'color': $el.css('color'),
                };
                $el.remove();

                this.$('.form-group .o_btn_preview.btn-' + type)
                    .css(_.pick(this.__realMMColors[type], 'background-color', 'color'));
            });
            $previewArea.remove();

            this._adaptPreview();
        });

        return ret;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _adaptPreview() {
        this._super(...arguments);
        if (this.__realMMColors) {
            var $preview = this.$("#link-preview");
            $preview.css('border-color', '');
            $preview.css('background-color', '');
            $preview.css('color', '');
            _.each(['link', 'primary', 'secondary'], type => {
                if ($preview.hasClass('btn-' + type) || type === 'link' && !$preview.hasClass('btn')) {
                    $preview.css(this.__realMMColors[type]);
                }
            });
        }
    },
});

});
