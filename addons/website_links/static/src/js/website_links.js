/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";
import publicWidget from "@web/legacy/js/public/public_widget";
import { addLoadingEffect } from '@web/core/utils/ui';
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import { attachComponent } from "@web_editor/js/core/owl_utils";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useService } from "@web/core/utils/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

class WebsiteLinksTagsWrapper extends Component {
    static template = "website_links.WebsiteLinksTagsWrapper";
    static components = { SelectMenu, DropdownItem };
    static props = {
        placeholder: { optional: true, type: String },
        model: { optional: true, type: String },
    };

    setup() {
        this.orm = useService("orm");
        this.keepLast = new KeepLast();
        this.state = useState({
            placeholder: this.props.placeholder,
            choices: [],
            value: undefined,
        });
        onWillStart(async () => {
            this.canCreateLinkTracker = await this.orm.call(this.props.model, "has_access", [[], "create"]);
            await this.loadChoice();
        });
    }

    get showCreateOption() {
        return this.select.data.searchValue && !this.state.choices.some(c => c.label === this.select.data.searchValue) && this.canCreateLinkTracker;
    }

    onSelect(value) {
        this.state.value = value;
    }

    async onCreateOption(string, closeFn) {
        const record = await this.orm.call("utm.mixin", "find_or_create_record", [
            this.props.model,
            string,
        ]);
        const choice = {
            label: record.name,
            value: record.id,
        };
        this.state.choices.push(choice);
        this.onSelect(choice.value);
    }

    loadChoice(searchString = "") {
        return new Promise((resolve, reject) => {
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
                ["id", "name"],
                {
                    limit: limit,
                    order: "name, id desc", // Allows to have exact match first
                },
            ];
            const proms = [];
            proms.push(
                this.orm.searchRead(
                    this.props.model,
                    // Exact match + results that start with the search
                    [["name", "=ilike", `${searchString}%`]],
                    ...searchReadParams
                )
            );
            proms.push(
                this.orm.searchRead(
                    this.props.model,
                    // Results that contain the search but do not start
                    // with it
                    [["name", "=ilike", `%_${searchString}%`]],
                    ...searchReadParams
                )
            );
            // Keep last is there in case a RPC takes longer than
            // the debounce delay + next rpc delay for some reason.
            this.keepLast
                .add(Promise.all(proms))
                .then(([startingMatches, endingMatches]) => {
                    const formatChoice = (choice) => {
                        choice.value = choice.id;
                        choice.label = choice.name;
                        return choice;
                    };
                    startingMatches.map(formatChoice);

                    // We loaded max a 2 * limit amount of records but
                    // ensure that we do not display "ending matches" if
                    // we may not have loaded all "starting matches".
                    if (startingMatches.length < limit) {
                        const startingMatchesId = startingMatches.map((value) => value.id);
                        const extraEndingMatches = endingMatches.filter(
                            (value) => !startingMatchesId.includes(value.id)
                        );
                        extraEndingMatches.map(formatChoice);
                        return startingMatches.concat(extraEndingMatches);
                    }
                    // In that case, we made one RPC too much but this
                    // was chosen over not making them go in parallel.
                    // We don't want to display "ending matches" if not
                    // all "starting matches" have been loaded.
                    return startingMatches;
                })
                .then((result) => {
                    this.state.choices = result;
                    resolve();
                })
                .catch(reject);
        });
    }
}

var RecentLinkBox = publicWidget.Widget.extend({
    template: 'website_links.RecentLink',
    events: {
        'click .btn_shorten_url_clipboard': '_onCopyShortenUrl',
    },

    /**
     * @constructor
     * @param {Object} parent
     * @param {Object} obj
     */
    init: function (parent, obj) {
        this._super.apply(this, arguments);
        this.link_obj = obj;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onCopyShortenUrl: async function (ev) {
        ev.preventDefault();
        const copyBtn = ev.currentTarget;
        const tooltip = Tooltip.getOrCreateInstance(copyBtn, {
            title: _t("Link Copied!"),
            trigger: "manual",
            placement: "top",
        });
        setTimeout(
            async () => await browser.navigator.clipboard.writeText(copyBtn.dataset.url)
        );
        tooltip.show();
        setTimeout(() => tooltip.hide(), 1200);
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
        const dropdownBtns = document.querySelectorAll('#recent_links_sort_by a');
        dropdownBtns.forEach((button) => {
            if (button.dataset.filter === filter) {
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
        'click #recent_links_sort_by a': '_onRecentLinksFilterChange',
        'click .o_website_links_new_link_tracker': '_onCreateNewLinkTrackerClick',
        'submit #o_website_links_link_tracker_form': '_onFormSubmit',
    },

    /**
     * @override
     */
    start: async function () {
        var defs = [this._super.apply(this, arguments)];

        async function attachSelectComponent(model, placeholderText, el) {
            const props = {
                placeholder: placeholderText,
                model: model,
            };
            await attachComponent(this, el, WebsiteLinksTagsWrapper, props);
        }

        attachSelectComponent.call(
            this,
            "utm.campaign",
            _t("e.g. June Sale, Paris Roadshow, ..."),
            this.el.querySelector("#campaign-select-wrapper"),
        );
        attachSelectComponent.call(
            this,
            "utm.medium",
            _t("e.g. InMails, Ads, Social, ..."),
            this.el.querySelector("#channel-select-wrapper"),
        );
        attachSelectComponent.call(
            this,
            "utm.source",
            _t("e.g. LinkedIn, Facebook, Leads, ..."),
            this.el.querySelector("#source-select-wrapper"),
        );

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
    _onRecentLinksFilterChange(ev) {
        this.recentLinks.removeLinks();
        this.recentLinks.getRecentLinks(ev.currentTarget.dataset.filter);
    },
    /**
     * @private
     * @param {Event} ev
     * Show the link tracker form back
     */
    _onCreateNewLinkTrackerClick: function (ev) {
        const utmForm = document.querySelector(".o_website_links_utm_forms");
        if (!utmForm.classList.contains("d-none")) {
            return;
        }
        utmForm.classList.remove("d-none");
        document.querySelector("#generated_tracked_link").classList.add("d-none");
        document.querySelector("#btn_shorten_url").classList.remove("d-none");
        document.querySelector("input#url").value = '';
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
        const campaignInputEl = document.querySelector("input[name='campaign-select']");
        const mediumInputEl = document.querySelector("input[name='medium-select']");
        const sourceInputEl = document.querySelector("input[name='source-select']");

        const label = document.querySelector('#label');
        const params = { label: label.value || undefined };
        params.url = $('#url').val();
        if (campaignInputEl.value !== "") {
            params.campaign_id = parseInt(campaignInputEl.value);
        }
        if (mediumInputEl.value !== "") {
            params.medium_id = parseInt(mediumInputEl.value);
        }
        if (sourceInputEl.value !== "") {
            params.source_id = parseInt(sourceInputEl.value);
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

                document.querySelector("#generated_tracked_link").classList.remove("d-none");
                document.querySelector("#btn_shorten_url").classList.add("d-none");

                document.querySelector(".copy-to-clipboard").dataset.clipboardText = link.short_url;
                document.querySelector("#short-url-host").textContent = link.short_url_host;
                document.querySelector("#o_website_links_code").textContent = link.code;

                self.recentLinks._addLink(link);

                // Clean notifications, URL and UTM selects
                $('.notification').html('');
                campaignInputEl.value = "";
                mediumInputEl.value = "";
                sourceInputEl.value = "";
                label.value = '';
                document.querySelector(".o_website_links_utm_forms").classList.add("d-none");
            }
        });
    },
});

export default {
    RecentLinkBox: RecentLinkBox,
    RecentLinks: RecentLinks,
};
