odoo.define('website.editor.link', function (require) {
'use strict';

var weWidgets = require('wysiwyg.widgets');
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
    LINK_DEBOUNCE: 1000,

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._adaptPageAnchor = _.debounce(this._adaptPageAnchor, this.LINK_DEBOUNCE);
    },
    /**
     * Allows the URL input to propose existing website pages.
     *
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        wUtils.autocompleteWithPages(this, this.$('input[name="url"]'));
        this.opened(this._adaptPageAnchor.bind(this));
        return def;
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
        if (!$pageAnchor.length) {
            return;
        }
        var isFromWebsite = urlInputValue[0] === '/';
        var $selectMenu = this.$('select[name="link_anchor"]');
        var $anchorsLoading = this.$('.o_anchors_loading');

        if ($selectMenu.data("anchor-for") !== urlInputValue) { // avoid useless query
            $anchorsLoading.removeClass('d-none');
            $pageAnchor.toggleClass('d-none', !isFromWebsite);
            $selectMenu.empty();
            const urlWithoutHash = urlInputValue.split("#")[0];
            wUtils.loadAnchors(urlWithoutHash).then(function (anchors) {
                _.each(anchors, function (anchor) {
                    $selectMenu.append($('<option>', {text: anchor}));
                });
                always();
            }).guardedCatch(always);
        } else {
            always();
        }

        function always() {
            $anchorsLoading.addClass('d-none');
            const anchor = `#${urlInputValue.split('#')[1]}`;
            let anchorIndex = -1;
            if (anchor) {
                const optionEls = $selectMenu[0].querySelectorAll('option');
                anchorIndex = Array.from(optionEls).findIndex(el => el.textContent === anchor);
            }
            $selectMenu.prop("selectedIndex", anchorIndex);
        }
        $selectMenu.data("anchor-for", urlInputValue);
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
