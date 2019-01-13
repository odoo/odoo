odoo.define('website.editor', function (require) {
'use strict';

var weWidgets = require('web_editor.widget');
var wUtils = require('website.utils');

weWidgets.LinkDialog.include({
    xmlDependencies: (weWidgets.LinkDialog.prototype.xmlDependencies || []).concat(
        ['/website/static/src/xml/website.editor.xml']
    ),
    events: _.extend({}, weWidgets.LinkDialog.prototype.events || {}, {
        'change select[name="link_anchor"]': '_onAnchorChange',
        'input input[name="url"]': '_onURLInput',
    }),
    custom_events: _.extend({}, weWidgets.LinkDialog.prototype.custom_events || {}, {
        website_url_chosen: '_onAutocompleteClose',
    }),

    /**
     * Allows the URL input to propose existing website pages.
     *
     * @override
     */
    start: function () {
        wUtils.autocompleteWithPages(this, this.$('input[name="url"]'));
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptPageAnchor: function () {
        var urlInputValue = this.$('input[name="url"]').val();
        var $pageAnchor = this.$('.o_link_dialog_page_anchor');
        var isFromWebsite = urlInputValue[0] === '/';
        var $selectMenu = this.$('select[name="link_anchor"]');
        var $anchorsLoading = this.$('.o_anchors_loading');

        $anchorsLoading.removeClass('d-none');
        $pageAnchor.toggleClass('d-none', !isFromWebsite);
        $selectMenu.empty();
        wUtils.loadAnchors(urlInputValue).then(function (anchors) {
            _.each(anchors, function (anchor) {
                $selectMenu.append($('<option>', {text: anchor}));
            });
        }).always(function () {
            $anchorsLoading.addClass('d-none');
            $selectMenu.prop("selectedIndex", -1);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAutocompleteClose: function () {
        this._onURLInput();
    },
    /**
     * @private
     */
    _onAnchorChange: function () {
        var anchorValue = this.$('[name="link_anchor"]').val();
        var $urlInput = this.$('[name="url"]');
        var urlInputValue = $urlInput.val();
        if (urlInputValue.indexOf('#') > -1) {
            urlInputValue = urlInputValue.substr(0, urlInputValue.indexOf('#'));
        }
        $urlInput.val(urlInputValue + anchorValue);
    },
    /**
     * @override
     */
    _onURLInput: function () {
        this._super.apply(this, arguments);
        this._adaptPageAnchor();
    },
});
});
