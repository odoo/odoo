/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { addLoadingEffect } from '@web/core/utils/ui';
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";

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
        this.keepLast = new KeepLast();
    },
    /**
     * @override
     */
    start: async function () {
        const canCreate = await this.orm.call(this.obj, "check_access_rights", [
            "create",
            false,
        ]);
        var self = this;
        this.$el.select2({
            placeholder: self.placeholder,
            allowClear: true,
            createSearchChoice: function (term) {
                if (!canCreate || self._objectExists(term)) {
                    return null;
                }
                return { id: term, text: `Create '${term}'` };
            },
            createSearchChoicePosition: 'bottom',
            multiple: false,
            ajax: {
                dataType: 'json',
                data: term => term,
                transport: (params, success, failure) => {
                    // Do not search immediately: wait for the user to stop
                    // typing (basically, this is a debounce).
                    clearTimeout(this._loadDataTimeout);
                    this._loadDataTimeout = setTimeout(() => {
                        // We want to search with a limit and not care about any
                        // pagination implementation. To make this work, we
                        // display the exact match first though, which requires
                        // an extra RPC (could be refactored into a new
                        // controller in master but... see TODO).
                        // TODO at some point this whole app will be moved as a
                        // backend screen, with real m2o fields etc... in which
                        // case the "exact match" feature should be handled by
                        // the ORM somehow ?
                        const limit = 100;
                        const searchReadParams = [
                            ['id', 'name'],
                            {
                                limit: limit,
                                order: 'name, id desc', // Allows to have exact match first
                            },
                        ];
                        const proms = [];
                        proms.push(this.orm.searchRead(
                            this.obj,
                            // Exact match + results that start with the search
                            [['name', '=ilike', `${params.data}%`]],
                            ...searchReadParams
                        ));
                        proms.push(this.orm.searchRead(
                            this.obj,
                            // Results that contain the search but do not start
                            // with it
                            [['name', '=ilike', `%_${params.data}%`]],
                            ...searchReadParams
                        ));
                        // Keep last is there in case a RPC takes longer than
                        // the debounce delay + next rpc delay for some reason.
                        this.keepLast.add(Promise.all(proms)).then(([startingMatches, endingMatches]) => {
                            // We loaded max a 2 * limit amount of records but
                            // ensure that we do not display "ending matches" if
                            // we may not have loaded all "starting matches".
                            if (startingMatches.length < limit) {
                                const startingMatchesId = startingMatches.map((value) => value.id);
                                const extraEndingMatches = endingMatches.filter(
                                    (value) => !startingMatchesId.includes(value.id)
                                );
                                return startingMatches.concat(extraEndingMatches);
                            }
                            // In that case, we made one RPC too much but this
                            // was chosen over not making them go in parallel.
                            // We don't want to display "ending matches" if not
                            // all "starting matches" have been loaded.
                            return startingMatches;
                        })
                        .then(params.success)
                        .catch(params.error);
                    }, 400);
                },
                results: data => {
                    this.objects = data.map(x => ({
                        id: x.id,
                        text: x.name,
                    }));
                    return {
                        results: this.objects,
                    };
                },
            },
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
        var args = {
            name: name
        };
        if (this.obj === "utm.campaign") {
            args.is_auto_campaign = true;
        }
        return this.orm.create(this.obj, [args]).then(record => {
            this.$el.attr('value', record);
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

    /**
     * @constructor
     * @param {Object} parent
     * @param {Object} obj
     */
    init: function (parent, obj) {
        this._super.apply(this, arguments);
        this.link_obj = obj;
    },
});

var RecentLinks = publicWidget.Widget.extend({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    getRecentLinks: function (filter) {
        var self = this;
        return rpc('/website_links/recent_links', {
            filter: filter,
            limit: 20,
        }).then(function (result) {
            result.reverse().forEach((link) => {
                self._addLink(link);
            });
            self._updateNotification();
            self._updateFilters(filter);
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
     * Updates the dropdown with the selected filter
     */
    _updateFilters: function(filter) {
        const dropdownBtns = document.querySelectorAll('[aria-labelledby="recent_links_sort_by"] a');
        dropdownBtns.forEach((button) => {
            if (button.id === `filter-${filter}-links`) {
                document.querySelector('.o_website_links_sort_by').textContent = button.textContent;
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
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
        'click #filter-last-clicked-links': '_onFilterLastClickedLinksClick',
        'click #generated_tracked_link a': '_onGeneratedTrackedLinkClick',
        'keyup #url': '_onUrlKeyUp',
        'click .btn_shorten_url_clipboard': '_onCopyShortenUrl',
        'submit #o_website_links_link_tracker_form': '_onFormSubmit',
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

        $('[data-bs-toggle="tooltip"]').tooltip();

        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCopyShortenUrl: async function (ev) {
        const copyBtn = ev.currentTarget;
        const tooltip = Tooltip.getOrCreateInstance(copyBtn, {
            title: _t("Link Copied!"),
            trigger: "manual",
            placement: "right",
        });
        setTimeout(
            async () => await browser.navigator.clipboard.writeText(copyBtn.dataset.url)
        );
        tooltip.show();
        setTimeout(() => tooltip.hide(), 1200);
    },

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
    _onFilterLastClickedLinksClick: function () {
        this.recentLinks.removeLinks();
        this.recentLinks.getRecentLinks('last-clicked');
    },
    /**
     * @private
     * @param {Event} ev
     * Show the link tracker form back when changing the target link after a link tracker has been generated
     */
    _onUrlKeyUp: function (ev) {
        const utmForm = document.querySelector(".o_website_links_utm_forms");
        if (!utmForm.classList.contains("d-none")) {
            return;
        }
        utmForm.classList.remove("d-none");
        document.querySelector(".link_tracked").classList.add("d-none");
        document.querySelector("#btn_shorten_url").classList.remove("d-none");
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
        const generateLinkTrackerBtn = document.querySelector("#btn_shorten_url");
        if (generateLinkTrackerBtn.classList.contains("d-none")) {
            return;
        }
        const restoreLoadingBtn = addLoadingEffect(generateLinkTrackerBtn);

        ev.stopPropagation();

        // Get URL and UTMs
        const campaignID = document.querySelector('#campaign-select').value;
        const mediumID = document.querySelector('#channel-select').value;
        const sourceID = document.querySelector('#source-select').value;

        const label = document.querySelector('#label');
        const params = { label: label.value || undefined };
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

        rpc('/website_links/new', params).then(function (result) {
            restoreLoadingBtn();
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

                document.querySelector(".link_tracked").classList.remove("d-none");
                document.querySelector("#btn_shorten_url").classList.add("d-none");

                document.querySelector(".btn_shorten_url_clipboard").dataset.url = link.short_url;
                document.querySelector("#generated_tracked_link").textContent = link.short_url;

                self.recentLinks._addLink(link);

                // Clean notifications, URL and UTM selects
                $('.notification').html('');
                $('#campaign-select').select2('val', '');
                $('#channel-select').select2('val', '');
                $('#source-select').select2('val', '');
                label.value = '';
                document.querySelector(".o_website_links_utm_forms").classList.add("d-none");
            }
        });
    },
});

export default {
    SelectBox: SelectBox,
    RecentLinkBox: RecentLinkBox,
    RecentLinks: RecentLinks,
};
