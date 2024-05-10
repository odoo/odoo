/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
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
            this.el.attr('value', record);
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

        this.animating_copy = true;
        const self = this;
        const originalElement = this.el.querySelector(".o_website_links_short_url");
        const top = originalElement.getBoundingClientRect().top + window.scrollY;
        const clonedElement = originalElement.cloneNode(true);
        Object.assign(clonedElement.style, {
            position: "absolute",
            left: "15px",
            top: `${top - 2}px`,
            zIndex: "2"
        });
        clonedElement.classList.replace("o_website_links_short_url", "animated-link");
        originalElement.parentNode.insertBefore(clonedElement, originalElement.nextSibling);
        clonedElement.animate([
            { opacity: 1, top: (top - 2) + "px" },
            { opacity: 0, top: (top - 22) + "px" }
        ], {
            duration: 500,
            fill: "forwards"
        }).onfinish = function() {
            clonedElement.remove();
            self.animating_copy = false;
        };
    },
    /**
     * @private
     * @param {String} message
     */
    _notification: function (message) {
        this.el.querySelector(".notification").append(`<strong>${message}</strong>`);
    },
    /**
     * @private
     */
    _editCode: function () {
        const initCode = this.el.querySelector("#o_website_links_code").innerHTML;
        this.el.querySelector(
            "#o_website_links_code"
        ).innerHTML = `<form style="display:inline;" id="o_website_links_edit_code_form">
                <input type="hidden" id="init_code" value="${initCode}"/>
                <input type="text" id="new_code" value="${initCode}"/>
            </form>`;
        this.el.querySelector(".o_website_links_edit_code").classList.toggle("d-none");
        this.el.querySelector(".copy-to-clipboard")?.classList.add("d-none");
        this.el.querySelector(".o_website_links_edit_tools").classList.toggle("d-none");
    },
    /**
     * @private
     */
    _cancelEdit: function () {
        this.el.querySelector(".o_website_links_edit_code").classList.toggle("d-none");
        this.el.querySelector(".copy-to-clipboard")?.classList.remove("d-none");
        this.el.querySelector(".o_website_links_edit_tools").classList.toggle("d-none");
        this.el.querySelector(".o_website_links_code_error").classList.toggle("d-none");

        const oldCode = this.el.querySelector("#o_website_links_edit_code_form #init_code").value;
        this.el.querySelector("#o_website_links_code").innerHTML = oldCode;

        this.el.querySelector("#code-error")?.remove();
        this.el.querySelector("#o_website_links_code form")?.remove();
    },
    /**
     * @private
     */
    _submitCode: function () {
        var self = this;

        const initCode = this.el.querySelector("#o_website_links_edit_code_form #init_code").value;
        const newCode = this.el.querySelector("#o_website_links_edit_code_form #new_code").value;

        if (newCode === '') {
            self.el.querySelector(".o_website_links_code_error").innerHTML = _t(
                "The code cannot be left empty"
            );
            self.el.querySelector(".o_website_links_code_error").style.display = "block";
            return;
        }

        function showNewCode(newCode) {
            self.el.querySelector(".o_website_links_code_error").innerHTML = "";
            self.el.querySelector(".o_website_links_code_error").classList.toggle("d-none");

            self.el.querySelector("#o_website_links_code form").remove();

            // Show new code
            const host = self.el.querySelector("#o_website_links_host").innerHTML;
            self.el.querySelector("#o_website_links_code").innerHTML = newCode;

            // Update button copy to clipboard
            self.el.querySelector(".btn_shorten_url_clipboard")
                .setAttribute("data-clipboard-text", host + newCode);

            // Show action again
            self.el.querySelector(".o_website_links_edit_code").classList.toggle("d-none");
            self.el.querySelector(".copy-to-clipboard")?.classList.remove("d-none");
            self.el.querySelector(".o_website_links_edit_tools").classList.toggle("d-none");
        }

        if (initCode === newCode) {
            showNewCode(newCode);
        } else {
            rpc('/website_links/add_code', {
                init_code: initCode,
                new_code: newCode,
            }).then(function (result) {
                showNewCode(result[0].code);
            }, function () {
                    self.el.querySelector(".o_website_links_code_error").classList.toggle("d-none");
                    self.el.querySelector(".o_website_links_code_error").innerHTML = _t(
                        "This code is already taken"
                    );
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
        }, function () {
                const message = _t("Unable to get recent links");
                self.el.append(
                    `<div class="alert alert-danger">${message}</div>`
                );
        });
    },
    /**
     * @private
     */
    _addLink: function (link) {
        const nbLinks = this.getChildren().length;
        const recentLinkBox = new RecentLinkBox(this, link);
        recentLinkBox.prependTo(this.el);
        document.querySelectorAll("[data-bs-toggle='tooltip']").forEach((tooltip) => {
            Tooltip.getOrCreateInstance(tooltip);
        });

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
            const message = _t("You don't have any recent links.");
            document.querySelector(
                ".o_website_links_recent_links_notification"
            ).innerHTML = `<div class="alert alert-info">${message}</div>`;
        } else {
            document.querySelector(".o_website_links_recent_links_notification").innerHTML = "";
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

    /**
     * @override
     */
    start: async function () {
        const defs = [this._super.apply(this, arguments)];

        // UTMS selects widgets
        const campaignSelect = new SelectBox(this, "utm.campaign", _t("e.g. June Sale, Paris Roadshow, ..."));
        defs.push(campaignSelect.attachTo(document.querySelector("#campaign-select")));

        const mediumSelect = new SelectBox(this, "utm.medium", _t("e.g. InMails, Ads, Social, ..."));
        defs.push(mediumSelect.attachTo(document.querySelector("#channel-select")));

        const sourceSelect = new SelectBox(this, "utm.source", _t("e.g. LinkedIn, Facebook, Leads, ..."));
        defs.push(sourceSelect.attachTo(document.querySelector("#source-select")));

        // Recent Links Widgets
        this.recentLinks = new RecentLinks(this.el);
        defs.push(this.recentLinks.attachTo(this.el.querySelector("#o_website_links_recent_links")));
        this.recentLinks.getRecentLinks("newest");

        this.url_copy_animating = false;

        Array.from(document.querySelectorAll("[data-bs-toggle='tooltip']")).forEach(function(node) {
            Tooltip.getOrCreateInstance(node);
        });

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
        const trackedLink = document.querySelector("#generated_tracked_link");
        trackedLink.textContent = _t("Copied");
        trackedLink.classList.remove("btn-primary");
        trackedLink.classList.add("btn-success");
        setTimeout(function () {
            trackedLink.textContent = _t("Copy");
            trackedLink.classList.remove("btn-success");
            trackedLink.classList.add("btn-primary");
        }, 5000);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUrlKeyUp: function (ev) {
        const shortenUrlButton = document.querySelector("#btn_shorten_url");
        if (!shortenUrlButton.classList.contains("btn-copy") || ev.key === "Enter") {
            return;
        }

        shortenUrlButton.classList.remove("btn-success", "btn-copy");
        shortenUrlButton.classList.add("btn-primary");
        shortenUrlButton.innerHTML = "Get tracked link";
        document.querySelector("#generated_tracked_link").style.display = "none";
        document.querySelector(".o_website_links_utm_forms").style.display = "block";
    },
    /**
     * @private
     */
    _onShortenUrlButtonClick: async function (ev) {
        const textValue = ev.target.dataset.clipboardText;
        await window.navigator.clipboard.writeText(textValue);

        const shortenUrlButton = document.querySelector("#btn_shorten_url");
        if (!shortenUrlButton.classList.contains("btn-copy") || this.url_copy_animating) {
            return;
        }

        const self = this;
        this.url_copy_animating = true;
        const originalElement = document.querySelector("#generated_tracked_link");
        const clonedElement = originalElement.cloneNode(true);
        Object.assign(clonedElement.style, {
            position: "absolute",
            left: "78px",
            zIndex: "2",
            transition: "opacity 0.8s, bottom 0.8s"
        });
        clonedElement.classList.remove("#generated_tracked_link");
        clonedElement.classList.add("url-animated-link");
        originalElement.appendChild(clonedElement);
        clonedElement.animate(
            [
                { opacity: 1, bottom: "8px" },
                { opacity: 0, bottom: "48px"}
            ],
            {
                duration: 500,
                fill: "forwards",
            }
        ).onfinish = function() {
            clonedElement.remove();
            self.url_copy_animating = false;
        };
    },
    /**
     * Add the RecentLinkBox widget and send the form when the user generate the link
     *
     * @private
     * @param {Event} ev
     */
    _onFormSubmit: function (ev) {
        const self = this;
        ev.preventDefault();

        if (document.querySelector("#btn_shorten_url").classList.contains("btn-copy")) {
            return;
        }

        ev.stopPropagation();

        // Get URL and UTMs
        const campaignID = document.querySelector('#campaign-select').value;
        const mediumID = document.querySelector('#channel-select').value;
        const sourceID = document.querySelector('#source-select').value;

        const label = document.querySelector('#label');
        const params = { label: label.value || undefined };
        params.url = document.querySelector("#url").value;
        if (campaignID !== '') {
            params.campaign_id = parseInt(campaignID);
        }
        if (mediumID !== '') {
            params.medium_id = parseInt(mediumID);
        }
        if (sourceID !== '') {
            params.source_id = parseInt(sourceID);
        }

        document.querySelector("#btn_shorten_url").textContent = _t("Generating link...");

        rpc('/website_links/new', params).then(function (result) {
            const notificationElement = document.querySelector(".notification");
            if ('error' in result) {
                // Handle errors
                if (result.error === 'empty_url') {
                    notificationElement.innerHTML = "<div class='alert alert-danger'>The URL is empty.</div>";
                } else if (result.error === "url_not_found") {
                    notificationElement.innerHTML = "<div class='alert alert-danger'>URL not found (404)</div>";
                } else {
                    notificationElement.innerHTML = "<div class='alert alert-danger'>An error occur while trying to generate your link. Try again later.</div>";
                }
            } else {
                // Link generated, clean the form and show the link
                var link = result[0];

                const btnShortenUrlElement = document.querySelector("#btn_shorten_url");
                btnShortenUrlElement.classList.remove("btn-primary");
                btnShortenUrlElement.classList.add("btn-success", "btn-copy");
                btnShortenUrlElement.innerHTML = "Copy";
                btnShortenUrlElement.setAttribute("data-clipboard-text", link.short_url);

                notificationElement.innerHTML = "";
                const generatedTrackedLinkEl = document.querySelector("#generated_tracked_link");
                generatedTrackedLinkEl.innerHTML = link.short_url;
                generatedTrackedLinkEl.style.display = "inline";

                self.recentLinks._addLink(link);

                // Clean URL and UTM selects
                document.querySelector("#campaign-select").value = "";
                document.querySelector("#channel-select").value = "";
                document.querySelector("#source-select").value = "";
                label.value = "";
                document.querySelector(".o_website_links_utm_forms").style.display = "none";
            }
        });
    },
});

export default {
    SelectBox: SelectBox,
    RecentLinkBox: RecentLinkBox,
    RecentLinks: RecentLinks,
};
