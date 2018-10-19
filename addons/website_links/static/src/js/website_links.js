odoo.define('website_links.website_links', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');
var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var _t = core._t;
var exports = {};

var SelectBox = Widget.extend({
    xmlDependencies: ['/website_links/static/src/xml/recent_link.xml'],
    /**
     * @override
     * @param {Object} obj
     */
    init: function (obj) {
        this.obj = obj;
    },
    /**
     * @override
     * @param {Object} parent
     * @param {Object} element
     * @param {String} placeholder
     */
    start: function (element, placeholder, parent) {
        var self = this;
        this.element = element;
        this.placeholder = placeholder;

        this._fetchObjects().then(function (results) {
            self.objects = results;

            element.select2({
                placeholder: self.placeholder,
                allowClear: true,
                createSearchChoice: function (term) {
                    if (self._objectExists(term)) { return null; }

                    return {id:term, text:_.str.sprintf("Create '%s'", term)};
                },
                createSearchChoicePosition: 'bottom',
                multiple: false,
                data: self.objects,
            });

            element.on('change', function (e) {
                self._onChange(e);
            });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _fetchObjects: function () {
        return this._rpc({
                model: this.obj,
                method: 'search_read',
            })
            .then(function (result) {
                return _.map(result, function (val) {
                    return {id: val.id, text:val.name};
                });
            });
    },
    /**
     * @private
     * @param {String} query
     */
    _objectExists: function (query) {
        return _.find(this.objects, function (val) {
            return val.text.toLowerCase() === query.toLowerCase();
        }) !== undefined;
    },
    /**
     * @private
     * @param {String} name
     */
    _createObject: function (name) {
        var self = this;
        return this._rpc({
                model: this.obj,
                method: 'create',
                args: [{name:name}],
            })
            .then(function (record) {
                self.element.attr('value', record);
                self.objects.push({'id': record, 'text': name});
            });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {Object} e
     */
    _onChange: function (e) {
        if (e.added && _.isString(e.added.id)) {
            this._createObject(e.added.id);
        }
    },

});

var RecentLinkBox = Widget.extend({
    template: 'website_links.RecentLink',
    events: {
        'click .btn_shorten_url_clipboard':'_toggleCopyButton',
        'click .o_website_links_edit_code':'_editCode',
        'click .o_website_links_ok_edit':function (e) {
            e.preventDefault();
            this._submitCode();
        },
        'click .o_website_links_cancel_edit': function (e) {
            e.preventDefault();
            this._cancelEdit();
        },
        'submit #o_website_links_edit_code_form': function (e) {
            e.preventDefault();
            this._submitCode();
        },
    },

    /**
     * @override
     * @param {Object} obj
     */
    init: function (parent, link_obj) {
        this._super(parent);
        this.link_obj = link_obj;
        this.animating_copy = false;
    },

    /**
     * @override
     * @param {Object} parent
     * @param {Object} element
     * @param {String} placeholder
     */
    start: function (element, placeholder, parent) {
        new ClipboardJS(this.$('.btn_shorten_url_clipboard').get(0));
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {String} query
     */
    _toggleCopyButton: function () {
        var self = this;

        if (!this.animating_copy) {
            this.animating_copy = true;
            var top = this.$('.o_website_links_short_url').position().top;
            this.$('.o_website_links_short_url').clone()
                .css('position', 'absolute')
                .css('left', 15)
                .css('top', top-2)
                .css('z-index', 2)
                .removeClass('o_website_links_short_url')
                .addClass('animated-link')
                .insertAfter(this.$('.o_website_links_short_url'))
                .animate({
                    opacity: 0,
                    top: "-=20",
                }, 500, function () {
                    self.$('.animated-link').remove();
                    self.animating_copy = false;
                });
        }
    },
    /**
     * @private
     */
    _remove: function () {
        this.getParent().remove_link(this);
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
        var init_code = this.$('#o_website_links_code').html();
        this.$('#o_website_links_code').html("<form style='display:inline;' id='o_website_links_edit_code_form'><input type='hidden' id='init_code' value='" + init_code + "'/><input type='text' id='new_code' value='" + init_code + "'/></form>");
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

        var old_code = this.$('#o_website_links_edit_code_form #init_code').val();
        this.$('#o_website_links_code').html(old_code);

        this.$('#code-error').remove();
        this.$('#o_website_links_code form').remove();
    },
    /**
     * @private
     */
    _submitCode: function () {
        var self = this;

        var init_code = this.$('#o_website_links_edit_code_form #init_code').val();
        var new_code = this.$('#o_website_links_edit_code_form #new_code').val();

        if (new_code === '') {
            self.$('.o_website_links_code_error').html("The code cannot be left empty");
            self.$('.o_website_links_code_error').show();
            return;
        }

        function ShowNewCode(new_code) {
            self.$('.o_website_links_code_error').html('');
            self.$('.o_website_links_code_error').hide();

            self.$('#o_website_links_code form').remove();

            // Show new code
            var host = self.$('#o_website_links_host').html();
            self.$('#o_website_links_code').html(new_code);

            // Update button copy to clipboard
            self.$('.btn_shorten_url_clipboard').attr('data-clipboard-text', host + new_code);

            // Show action again
            self.$('.o_website_links_edit_code').show();
            self.$('.copy-to-clipboard').show();
            self.$('.o_website_links_edit_tools').hide();
        }

        if (init_code === new_code) {
            ShowNewCode(new_code);
        }
        else {
            ajax.jsonRpc('/website_links/add_code', 'call', {'init_code':init_code, 'new_code':new_code})
                .then(function (result) {
                    ShowNewCode(result[0].code);
                })
                .fail(function () {
                    self.$('.o_website_links_code_error').show();
                    self.$('.o_website_links_code_error').html("This code is already taken");
                }) ;
        }
    },

});

var RecentLinks = Widget.extend({
    /**
     * @override
     */
    init: function () {
        this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _getRecentLinks: function (filter) {
        var self = this;
        ajax.jsonRpc('/website_links/recent_links', 'call', {'filter':filter, 'limit':20})
            .then(function (result) {
                _.each(result.reverse(), function (link) {
                    self._addLink(link);
                });

                self._updateNotification();
            })
            .fail(function () {
                var message = _t("Unable to get recent links");
                self.$el.append("<div class='alert alert-danger'>" + message + "</div>");
            });
    },
    /**
     * @private
     */
    _addLink: function (link) {
        var nb_links = this.getChildren().length;
        var recent_link_box = new RecentLinkBox(this, link);
        recent_link_box.prependTo(this.$el);
        $('.link-tooltip').tooltip();

        if (nb_links === 0) {
            this._updateNotification();
        }
    },
    /**
     * @private
     */
    _removeLinks: function () {
        $('#o_website_links_recent_links .link-row').each(function () {
            this.remove();
        });
    },
    /**
     * @private
     */
    _removeLink: function (link) {
        link.destroy();
    },
    /**
     * @private
     */
    _updateNotification: function () {
        if (this.getChildren().length === 0) {
            var message = _t("You don't have any recent links.");
            $('.o_website_links_recent_links_notification').html("<div class='alert alert-info'>" + message + "</div>");
        }
        else {
            $('.o_website_links_recent_links_notification').empty();
        }
    },

});

sAnimations.registry.websiteLinks = sAnimations.Class.extend({
    selector: '.o_website_links_create_tracked_url',
    read_events: {
        'click #filter-newest-links': '_onFilterNewestLinks',
        'click #filter-most-clicked-links': '_onFilterMostClickedLinks',
        'click #filter-recently-used-links': '_onFilterRecentlyUsedLinks',
        'click #generated_tracked_link a': '_onGeneratedTrackedLink',
        'keyup #url': '_onUrlKeyUp',
        'click #btn_shorten_url': '_onBtnShortenUrl',
        'submit #o_website_links_link_tracker_form': '_onSubmitForm'
    },

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        // UTMS selects widgets
        var campaign_select = new SelectBox('utm.campaign');
        campaign_select.start($("#campaign-select"), _t('e.g. Promotion of June, Winter Newsletter, ..'));

        var medium_select = new SelectBox('utm.medium');
        medium_select.start($("#channel-select"), _t('e.g. Newsletter, Social Network, ..'));

        var source_select = new SelectBox('utm.source');
        source_select.start($("#source-select"), _t('e.g. Search Engine, Website page, ..'));

        // Recent Links Widgets
        this.recent_links = new RecentLinks();
        this.recent_links.appendTo($("#o_website_links_recent_links"));
        this.recent_links._getRecentLinks('newest');

        // Clipboard Library
        new ClipboardJS($("#btn_shorten_url").get(0));

        this.url_copy_animating = false;

        $(function () {
            $('[data-toggle="tooltip"]').tooltip();
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onFilterNewestLinks: function () {
        this.recent_links._removeLinks();
        this.recent_links._getRecentLinks('newest');
    },
    /**
     * @override
     */
    _onFilterMostClickedLinks: function () {
        this.recent_links._removeLinks();
        this.recent_links._getRecentLinks('most-clicked');
    },
    /**
     * @override
     */
    _onFilterRecentlyUsedLinks: function () {
        this.recent_links._removeLinks();
        this.recent_links._getRecentLinks('recently-used');
    },
    /**
     * @override
     */
    _onGeneratedTrackedLink: function () {
        $("#generated_tracked_link a").text("Copied").removeClass("btn-primary").addClass("btn-success");
        setTimeout(function () {
            $("#generated_tracked_link a").text("Copy").removeClass("btn-success").addClass("btn-primary");
        }, '5000');
    },
    /**
     * @override
     * @param {Object} e
     */
    _onUrlKeyUp: function (e) {
        if ($('#btn_shorten_url').hasClass('btn-copy') && e.which !== 13) {
            $('#btn_shorten_url').removeClass('btn-success btn-copy').addClass('btn-primary').html('Get tracked link');
            $('#generated_tracked_link').css('display', 'none');
            $('.o_website_links_utm_forms').show();
        }
    },
    /**
     * @override
     */
    _onBtnShortenUrl: function () {
        if ($('#btn_shorten_url').hasClass('btn-copy')) {
            if (!this.url_copy_animating) {
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
                        bottom: "+=20",
                    }, 500, function () {
                        $('.url-animated-link').remove();
                        this.url_copy_animating = false;
                    });
            }
        }
    },
    /**
     * Add the RecentLinkBox widget and send the form when the user generate the link
     *
     * @override
     * @param {Object} ev
     */
    _onSubmitForm: function (ev) {
        if ($('#btn_shorten_url').hasClass('btn-copy')) {
            ev.preventDefault();
            return;
        }

        ev.preventDefault();
        ev.stopPropagation();

        // Get URL and UTMs
        var campaign_id = $('#campaign-select').attr('value');
        var medium_id = $('#channel-select').attr('value');
        var source_id = $('#source-select').attr('value');

        var params = {};
        params.url = $("#url").val();
        if (campaign_id !== '') { params.campaign_id = parseInt(campaign_id); }
        if (medium_id !== '') { params.medium_id = parseInt(medium_id); }
        if (source_id !== '') { params.source_id = parseInt(source_id); }

        $('#btn_shorten_url').text(_t('Generating link...'));

        ajax.jsonRpc("/website_links/new", 'call', params)
            .then(function (result) {
                if ('error' in result) {
                    // Handle errors
                    if (result.error === 'empty_url')  {
                        $('.notification').html("<div class='alert alert-danger'>The URL is empty.</div>");
                    }
                    else if (result.error === 'url_not_found') {
                        $('.notification').html("<div class='alert alert-danger'>URL not found (404)</div>");
                    }
                    else {
                        $('.notification').html("<div class='alert alert-danger'>An error occur while trying to generate your link. Try again later.</div>");
                    }
                }
                else {
                    // Link generated, clean the form and show the link
                    var link = result[0];

                    $('#btn_shorten_url').removeClass('btn-primary').addClass('btn-success btn-copy').html('Copy');
                    $('#btn_shorten_url').attr('data-clipboard-text', link.short_url);

                    $('.notification').html('');
                    $('#generated_tracked_link').html(link.short_url);
                    $('#generated_tracked_link').css('display', 'inline');

                    this.recent_links._addLink(link);

                    // Clean URL and UTM selects
                    $('#campaign-select').select2('val', '');
                    $('#channel-select').select2('val', '');
                    $('#source-select').select2('val', '');

                    $('.o_website_links_utm_forms').hide();
                }
            });
    },

});

exports.SelectBox = SelectBox;
exports.RecentLinkBox = RecentLinkBox;
exports.RecentLinks = RecentLinks;

return exports;

});
