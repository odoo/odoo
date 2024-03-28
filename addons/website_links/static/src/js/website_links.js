/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { browser } from "@web/core/browser/browser";

var SelectBox = publicWidget.Widget.extend({
    events: {
        'change': '_onChange',
    },

    /**
     * @constructor
     * @param {Object} parent
     * @param {Object} obj
     * @param {String} placeholder
     */
    init: function (parent, obj, placeholder) {
        this._super.apply(this, arguments);
        this.obj = obj;
        this.placeholder = placeholder;

        this.orm = this.bindService("orm");
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        defs.push(this.orm.searchRead(this.obj, [], ["id", "name"]).then(function (result) {
            self.objects = result.map((val) => {
                return {id: val.id, text: val.name};
            });
        }));
        return Promise.all(defs);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$el.select2({
            placeholder: self.placeholder,
            allowClear: true,
            createSearchChoice: function (term) {
                if (self._objectExists(term)) {
                    return null;
                }
                return { id: term, text: `Create '${term}'` };
            },
            createSearchChoicePosition: 'bottom',
            multiple: false,
            data: self.objects,
            minimumInputLength: self.objects.length > 100 ? 3 : 0,
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {String} query
     */
    _objectExists: function (query) {
        return this.objects.find(val => val.text.toLowerCase() === query.toLowerCase()) !== undefined;
    },
    /**
     * @private
     * @param {String} name
     */
    _createObject: function (name) {
        var self = this;
        var args = {
            name: name
        };
        if (this.obj === "utm.campaign"){
            args.is_auto_campaign = true;
        }
        return this.orm.create(this.obj, [args]).then(function (record) {
            self.$el.attr('value', record);
            self.objects.push({'id': record, 'text': name});
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} ev
     */
    _onChange: function (ev) {
        if (!ev.added || typeof ev.added.id !== "string") {
            return;
        }
        this._createObject(ev.added.id);
    },
});

var RecentLinkBox = publicWidget.Widget.extend({
    template: 'website_links.RecentLink',
    events: {
        'click .btn_shorten_url_clipboard': '_toggleCopyButton',
        'click .o_website_links_edit_code': '_editCode',
        'click .o_website_links_ok_edit': '_onLinksOkClick',
        'click .o_website_links_cancel_edit': '_onLinksCancelClick',
        'submit #o_website_links_edit_code_form': '_onSubmitCode',
    },

    /**
     * @constructor
     * @param {Object} parent
     * @param {Object} obj
     */
    init: function (parent, obj) {
        this._super.apply(this, arguments);
        this.link_obj = obj;
        this.animating_copy = false;
        this.rpc = this.bindService("rpc");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _toggleCopyButton: async function () {
        await browser.navigator.clipboard.writeText(this.link_obj.short_url);

        if (this.animating_copy) {
            return;
        }

        var self = this;
        this.animating_copy = true;
        var top = this.$('.o_website_links_short_url').position().top;
        this.$('.o_website_links_short_url').clone()
            .css('position', 'absolute')
            .css('left', 15)
            .css('top', top - 2)
            .css('z-index', 2)
            .removeClass('o_website_links_short_url')
            .addClass('animated-link')
            .insertAfter(this.$('.o_website_links_short_url'))
            .animate({
                opacity: 0,
                top: '-=20',
            }, 500, function () {
                self.$('.animated-link').remove();
                self.animating_copy = false;
            });
    },
    /**
     * @private
     * @param {String} message
     */
    _notification: function (message) {
        this.$('.notification').append('<strong>' + message + '</strong>');
    },
    /**
     * @private
     */
    _editCode: function () {
        var initCode = this.$('#o_website_links_code').html();
        this.$('#o_website_links_code').html('<form style="display:inline;" id="o_website_links_edit_code_form"><input type="hidden" id="init_code" value="' + initCode + '"/><input type="text" id="new_code" value="' + initCode + '"/></form>');
        this.$('.o_website_links_edit_code').hide();
        this.$('.copy-to-clipboard').hide();
        this.$('.o_website_links_edit_tools').show();
    },
    /**
     * @private
     */
    _cancelEdit: function () {
        this.$('.o_website_links_edit_code').show();
        this.$('.copy-to-clipboard').show();
        this.$('.o_website_links_edit_tools').hide();
        this.$('.o_website_links_code_error').hide();

        var oldCode = this.$('#o_website_links_edit_code_form #init_code').val();
        this.$('#o_website_links_code').html(oldCode);

        this.$('#code-error').remove();
        this.$('#o_website_links_code form').remove();
    },
    /**
     * @private
     */
    _submitCode: function () {
        var self = this;

        var initCode = this.$('#o_website_links_edit_code_form #init_code').val();
        var newCode = this.$('#o_website_links_edit_code_form #new_code').val();

        if (newCode === '') {
            self.$('.o_website_links_code_error').html(_t("The code cannot be left empty"));
            self.$('.o_website_links_code_error').show();
            return;
        }

        function showNewCode(newCode) {
            self.$('.o_website_links_code_error').html('');
            self.$('.o_website_links_code_error').hide();

            self.$('#o_website_links_code form').remove();

            // Show new code
            var host = self.$('#o_website_links_host').html();
            self.$('#o_website_links_code').html(newCode);

            // Update button copy to clipboard
            self.$('.btn_shorten_url_clipboard').attr('data-clipboard-text', host + newCode);

            // Show action again
            self.$('.o_website_links_edit_code').show();
            self.$('.copy-to-clipboard').show();
            self.$('.o_website_links_edit_tools').hide();
        }

        if (initCode === newCode) {
            showNewCode(newCode);
        } else {
            this.rpc('/website_links/add_code', {
                init_code: initCode,
                new_code: newCode,
            }).then(function (result) {
                showNewCode(result[0].code);
            }, function () {
                self.$('.o_website_links_code_error').show();
                self.$('.o_website_links_code_error').html(_t("This code is already taken"));
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onLinksOkClick: function (ev) {
        ev.preventDefault();
        this._submitCode();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onLinksCancelClick: function (ev) {
        ev.preventDefault();
        this._cancelEdit();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSubmitCode: function (ev) {
        ev.preventDefault();
        this._submitCode();
    },
});

var RecentLinks = publicWidget.Widget.extend({
    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    getRecentLinks: function (filter) {
        var self = this;
        return this.rpc('/website_links/recent_links', {
            filter: filter,
            limit: 20,
        }).then(function (result) {
            result.reverse().forEach((link) => {
                self._addLink(link);
            });
            self._updateNotification();
        }, function () {
            var message = _t("Unable to get recent links");
            self.$el.append('<div class="alert alert-danger">' + message + '</div>');
        });
    },
    /**
     * @private
     */
    _addLink: function (link) {
        var nbLinks = this.getChildren().length;
        var recentLinkBox = new RecentLinkBox(this, link);
        recentLinkBox.prependTo(this.$el);
        $('.link-tooltip').tooltip();

        if (nbLinks === 0) {
            this._updateNotification();
        }
    },
    /**
     * @private
     */
    removeLinks: function () {
        this.getChildren().forEach((child) => {
            child.destroy();
        });
    },
    /**
     * @private
     */
    _updateNotification: function () {
        if (this.getChildren().length === 0) {
            var message = _t("You don't have any recent links.");
            $('.o_website_links_recent_links_notification').html('<div class="alert alert-info">' + message + '</div>');
        } else {
            $('.o_website_links_recent_links_notification').empty();
        }
    },
});

publicWidget.registry.websiteLinks = publicWidget.Widget.extend({
    selector: '.o_website_links_create_tracked_url',
    events: {
        'click #filter-newest-links': '_onFilterNewestLinksClick',
        'click #filter-most-clicked-links': '_onFilterMostClickedLinksClick',
        'click #filter-recently-used-links': '_onFilterRecentlyUsedLinksClick',
        'click #generated_tracked_link a': '_onGeneratedTrackedLinkClick',
        'keyup #url': '_onUrlKeyUp',
        'click #btn_shorten_url': '_onShortenUrlButtonClick',
        'submit #o_website_links_link_tracker_form': '_onFormSubmit',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    /**
     * @override
     */
    start: async function () {
        var defs = [this._super.apply(this, arguments)];

        // UTMS selects widgets
        const campaignSelect = new SelectBox(this, "utm.campaign", _t("e.g. June Sale, Paris Roadshow, ..."));
        defs.push(campaignSelect.attachTo($('#campaign-select')));

        const mediumSelect = new SelectBox(this, "utm.medium", _t("e.g. InMails, Ads, Social, ..."));
        defs.push(mediumSelect.attachTo($('#channel-select')));

        const sourceSelect = new SelectBox(this, "utm.source", _t("e.g. LinkedIn, Facebook, Leads, ..."));
        defs.push(sourceSelect.attachTo($('#source-select')));

        // Recent Links Widgets
        this.recentLinks = new RecentLinks(this);
        defs.push(this.recentLinks.appendTo($('#o_website_links_recent_links')));
        this.recentLinks.getRecentLinks('newest');

        this.url_copy_animating = false;

        $('[data-bs-toggle="tooltip"]').tooltip();

        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onFilterNewestLinksClick: function () {
        this.recentLinks.removeLinks();
        this.recentLinks.getRecentLinks('newest');
    },
    /**
     * @private
     */
    _onFilterMostClickedLinksClick: function () {
        this.recentLinks.removeLinks();
        this.recentLinks.getRecentLinks('most-clicked');
    },
    /**
     * @private
     */
    _onFilterRecentlyUsedLinksClick: function () {
        this.recentLinks.removeLinks();
        this.recentLinks.getRecentLinks('recently-used');
    },
    /**
     * @private
     */
    _onGeneratedTrackedLinkClick: function () {
        $('#generated_tracked_link a').text(_t("Copied")).removeClass('btn-primary').addClass('btn-success');
        setTimeout(function () {
            $('#generated_tracked_link a').text(_t("Copy")).removeClass('btn-success').addClass('btn-primary');
        }, 5000);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUrlKeyUp: function (ev) {
        if (!$('#btn_shorten_url').hasClass('btn-copy') || ev.key === "Enter") {
            return;
        }

        $('#btn_shorten_url').removeClass('btn-success btn-copy').addClass('btn-primary').html('Get tracked link');
        $('#generated_tracked_link').css('display', 'none');
        $('.o_website_links_utm_forms').show();
    },
    /**
     * @private
     */
    _onShortenUrlButtonClick: async function (ev) {
        const textValue = ev.target.dataset.clipboardText;
        await browser.navigator.clipboard.writeText(textValue);

        if (!$('#btn_shorten_url').hasClass('btn-copy') || this.url_copy_animating) {
            return;
        }

        var self = this;
        this.url_copy_animating = true;
        $('#generated_tracked_link').clone()
            .css('position', 'absolute')
            .css('left', '78px')
            .css('bottom', '8px')
            .css('z-index', 2)
            .removeClass('#generated_tracked_link')
            .addClass('url-animated-link')
            .appendTo($('#generated_tracked_link'))
            .animate({
                opacity: 0,
                bottom: '+=20',
            }, 500, function () {
                $('.url-animated-link').remove();
                self.url_copy_animating = false;
            });
    },
    /**
     * Add the RecentLinkBox widget and send the form when the user generate the link
     *
     * @private
     * @param {Event} ev
     */
    _onFormSubmit: function (ev) {
        var self = this;
        ev.preventDefault();

        if ($('#btn_shorten_url').hasClass('btn-copy')) {
            return;
        }

        ev.stopPropagation();

        // Get URL and UTMs
        var campaignID = $('#campaign-select').attr('value');
        var mediumID = $('#channel-select').attr('value');
        var sourceID = $('#source-select').attr('value');

        var params = {};
        params.url = $('#url').val();
        if (campaignID !== '') {
            params.campaign_id = parseInt(campaignID);
        }
        if (mediumID !== '') {
            params.medium_id = parseInt(mediumID);
        }
        if (sourceID !== '') {
            params.source_id = parseInt(sourceID);
        }

        $('#btn_shorten_url').text(_t("Generating link..."));

        this.rpc('/website_links/new', params).then(function (result) {
            if ('error' in result) {
                // Handle errors
                if (result.error === 'empty_url') {
                    $('.notification').html('<div class="alert alert-danger">The URL is empty.</div>');
                } else if (result.error === 'url_not_found') {
                    $('.notification').html('<div class="alert alert-danger">URL not found (404)</div>');
                } else {
                    $('.notification').html('<div class="alert alert-danger">An error occur while trying to generate your link. Try again later.</div>');
                }
            } else {
                // Link generated, clean the form and show the link
                var link = result[0];

                $('#btn_shorten_url').removeClass('btn-primary').addClass('btn-success btn-copy').html('Copy');
                $('#btn_shorten_url').attr('data-clipboard-text', link.short_url);

                $('.notification').html('');
                $('#generated_tracked_link').html(link.short_url);
                $('#generated_tracked_link').css('display', 'inline');

                self.recentLinks._addLink(link);

                // Clean URL and UTM selects
                $('#campaign-select').select2('val', '');
                $('#channel-select').select2('val', '');
                $('#source-select').select2('val', '');

                $('.o_website_links_utm_forms').hide();
            }
        });
    },
});

export default {
    SelectBox: SelectBox,
    RecentLinkBox: RecentLinkBox,
    RecentLinks: RecentLinks,
};
