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
     * Explicitly override becuase setCursor will keep focus on Image and
     * when you click next time on Image will consider as a click on Anchor tag
     * leads to open Text tools instead of Image tools.
     */
    destroy: function () {
        this._super(...arguments);
        $('.oe_edited_link').removeClass('oe_edited_link');
    },
});

return ImageLinkTools;
});
