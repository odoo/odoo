odoo.define('wysiwyg.widgets.ImageLinkTools', function (require) {
'use strict';
const LinkTools = require('wysiwyg.widgets.LinkTools');
/**
 * Allows to customize Image link content and style.
 */
const ImageLinkTools = LinkTools.extend({
    template: 'wysiwyg.widgets.imageLinkTools',
    /**
     * @override
     */
    start: function () {
        if (this.data.isNewWindow) {
            if (this.$el && this.$el[0].querySelector("#is_new_window")) {
                this.$el[0].querySelector("#is_new_window").closest(".o_we_checkbox_wrapper").classList.toggle('active');
            }
        }
        return this._super(...arguments);
    },
    /**
     * @override
     * Explicitly override becuase setCursor will keep focus on Image and
     * when you click next time on Image will consider as a click on Anchor tag
     * leads to open Text tools instead of Image tools.
     */
    destroy: function () {
        this._super(...arguments);
        this.$link.removeClass('oe_edited_link');
    },
});
return ImageLinkTools;
});
