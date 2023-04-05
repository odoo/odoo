/** @odoo-module alias=wysiwyg.widgets.AltDialog **/

import core from "web.core";
import Dialog from "wysiwyg.widgets.Dialog";

var _t = core._t;

/**
 * Let users change the alt & title of a media.
 */
var AltDialog = Dialog.extend({
    template: 'wysiwyg.widgets.alt',
    /**
     * @constructor
     */
    init: function (parent, options, media) {
        options = options || {};
        this._super(parent, Object.assign({}, {
            title: _t("Change media description and tooltip")
        }, options));

        this.media = media;
        var allEscQuots = /&quot;/g;
        this.alt = ($(this.media).attr('alt') || "").replace(allEscQuots, '"');
        var title = $(this.media).attr('title') || $(this.media).data('original-title') || "";
        this.tag_title = (title).replace(allEscQuots, '"');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        var alt = this.$('#alt').val();
        var title = this.$('#title').val();
        var allNonEscQuots = /"/g;
        $(this.media).attr('alt', alt ? alt.replace(allNonEscQuots, "&quot;") : null)
            .attr('title', title ? title.replace(allNonEscQuots, "&quot;") : null);
        $(this.media).trigger('content_changed');
        this.final_data = this.media;
        return this._super.apply(this, arguments);
    },
});


export default AltDialog;
