odoo.define('wysiwyg.widgets.AltDialog', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('wysiwyg.widgets.Dialog');

var _t = core._t;

/**
 * Let users change the alt & title of a media.
 */
var AltDialog = Dialog.extend({
    template: 'wysiwyg.widgets.alt',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/wysiwyg.xml']
    ),

    /**
     * @constructor
     */
    init: function (parent, options, media) {
        options = options || {};
        this._super(parent, _.extend({}, {
            title: _t("Change media description and tooltip")
        }, options));

        this.trigger_up('getRecordInfo', {
            recordInfo: options,
            callback: function (recordInfo) {
                _.defaults(options, recordInfo);
            },
        });

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


return AltDialog;
});
