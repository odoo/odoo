odoo.define('website.s_facebook_page_options', function (require) {
'use strict';

const core = require('web.core');
const weWidgets = require('wysiwyg.widgets');
const options = require('web_editor.snippets.options');

const _t = core._t;

const FacebookPageDialog = weWidgets.Dialog.extend({
    xmlDependencies: weWidgets.Dialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/website.facebook_page.xml']
    ),
    template: 'website.facebook_page_dialog',
    events: _.extend({}, weWidgets.Dialog.prototype.events || {}, {
        'change': '_onOptionChange',
    }),

    /**
     * @constructor
     */
    init: function (parent, fbData, options) {
        this._super(parent, _.extend({
            title: _t("Facebook Page"),
        }, options || {}));

        this.fbData = $.extend(true, {}, fbData);
        this.final_data = this.fbData;
    },
    /**
     * @override
     */
    start: function () {
        this.$previewPage = this.$('.o_facebook_page');
        this.opened().then(this._renderPreview.bind(this));
        return this._super.apply(this, arguments);
    },

    //------------------------------------------------------------------
    // Private
    //------------------------------------------------------------------

    /**
     * Manages Facebook page preview. Also verifies if the page exists on
     * Facebook or not.
     *
     * @private
     */
    _renderPreview: function () {
        var self = this;
        var match = this.fbData.href.match(/^(?:https?:\/\/)?(?:www\.)?(?:fb|facebook)\.com\/(?:([\w.]+)|[^/?#]+-([0-9]{15,16}))(?:$|[/?# ])/);
        if (match) {
            // Check if the page exists on Facebook or not
            $.ajax({
                url: 'https://graph.facebook.com/' + (match[2] || match[1]) + '/picture',
                statusCode: {
                    200: function () {
                        self._toggleWarning(true);

                        // Managing height based on options
                        if (self.fbData.tabs) {
                            self.fbData.height = self.fbData.tabs === 'events' ? 300 : 500;
                        } else if (self.fbData.small_header) {
                            self.fbData.height = self.fbData.show_facepile ? 165 : 70;
                        } else if (!self.fbData.small_header) {
                            self.fbData.height = self.fbData.show_facepile ? 225 : 150;
                        }
                        options.registry.facebookPage.prototype.markFbElement(self.getParent(), self.$previewPage, self.fbData);
                    },
                    404: function () {
                        self._toggleWarning(false);
                    },
                },
            });
        } else {
            this._toggleWarning(false);
        }
    },
    /**
     * Toggles the warning message and save button and destroy iframe preview.
     *
     * @private
     * @param {boolean} toggle
     */
    _toggleWarning: function (toggle) {
        this.trigger_up('widgets_stop_request', {
            $target: this.$previewPage,
        });
        this.$('.facebook_page_warning').toggleClass('d-none', toggle);
        this.$footer.find('.btn-primary').prop('disabled', !toggle);
    },

    //------------------------------------------------------------------
    // Handlers
    //------------------------------------------------------------------

    /**
     * Called when a facebook option is changed -> adapt the preview and saved
     * data.
     *
     * @private
     */
    _onOptionChange: function () {
        var self = this;
        // Update values in fbData
        this.fbData.tabs = _.map(this.$('.o_facebook_tabs input:checked'), tab => tab.name).join(',');
        this.fbData.href = this.$('.o_facebook_page_url').val();
        _.each(this.$('.o_facebook_options input'), function (el) {
            self.fbData[el.name] = $(el).prop('checked');
        });
        this._renderPreview();
    },
});
options.registry.facebookPage = options.Class.extend({
    /**
     * Initializes the required facebook page data to create the iframe.
     *
     * @override
     */
    willStart: function () {
        var defs = [this._super.apply(this, arguments)];

        var defaults = {
            href: false,
            height: 215,
            width: 350,
            tabs: '',
            small_header: false,
            hide_cover: false,
            show_facepile: false,
        };
        this.fbData = _.defaults(_.pick(this.$target.data(), _.keys(defaults)), defaults);

        if (!this.fbData.href) {
            // Fetches the default url for facebook page from website config
            var self = this;
            defs.push(this._rpc({
                model: 'website',
                method: 'search_read',
                args: [[], ['social_facebook']],
                limit: 1,
            }).then(function (res) {
                if (res) {
                    self.fbData.href = res[0].social_facebook || 'https://www.facebook.com/Odoo';
                }
            }));
        }

        return Promise.all(defs);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$target.on('click.facebook_page_option', '.o_add_facebook_page', function (ev) {
            ev.preventDefault();
            self.fbPageOptions();
        });
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$target.off('.facebook_page_option');
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Opens a dialog to configure the facebook page options.
     *
     * @see this.selectClass for parameters
     */
    fbPageOptions: function () {
        var dialog = new FacebookPageDialog(this, this.fbData).open();
        dialog.on('save', this, function (fbData) {
            this.$target.empty();
            this.fbData = fbData;
            options.registry.facebookPage.prototype.markFbElement(this, this.$target, this.fbData);
        });
    },

    //--------------------------------------------------------------------------
    // Static
    //--------------------------------------------------------------------------

    /**
     * @static
     */
    markFbElement: function (self, $el, fbData) {
        _.each(fbData, function (value, key) {
            $el.attr('data-' + key, value);
            $el.data(key, value);
        });
        self._refreshPublicWidgets($el);
    },
});
});
