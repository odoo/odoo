odoo.define('website.s_facebook_page_options', function (require) {
'use strict';

const core = require('web.core');
const options = require('web_editor.snippets.options');

const _t = core._t;

options.registry.facebookPage = options.Class.extend({
    /**
     * Initializes the required facebook page data to create the iframe.
     *
     * @override
     */
    willStart: function () {
        var defs = [this._super.apply(this, arguments)];

        var defaults = {
            href: '',
            id: '',
            height: 215,
            width: 350,
            tabs: '',
            small_header: true,
            hide_cover: true,
        };
        this.fbData = _.defaults(_.pick(this.$target[0].dataset, _.keys(defaults)), defaults);

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
                    self.fbData.href = res[0].social_facebook || '';
                }
            }));
        }

        return Promise.all(defs).then(() => this._markFbElement()).then(() => this._refreshPublicWidgets());
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Toggles a checkbox option.
     *
     * @see this.selectClass for parameters
     * @param {String} optionName the name of the option to toggle
     */
    toggleOption: function (previewMode, widgetValue, params) {
        let optionName = params.optionName;
        if (optionName.startsWith('tab.')) {
            optionName = optionName.replace('tab.', '');
            if (widgetValue) {
                this.fbData.tabs = this.fbData.tabs
                    .split(',')
                    .filter(t => t !== '')
                    .concat([optionName])
                    .join(',');
            } else {
                this.fbData.tabs = this.fbData.tabs
                    .split(',')
                    .filter(t => t !== optionName)
                    .join(',');
            }
        } else {
            if (optionName === 'show_cover') {
                this.fbData.hide_cover = !widgetValue;
            } else {
                this.fbData[optionName] = widgetValue;
            }
        }
        return this._markFbElement();
    },
    /**
     * Sets the facebook page's URL.
     *
     * @see this.selectClass for parameters
     */
    pageUrl: function (previewMode, widgetValue, params) {
        this.fbData.href = widgetValue;
        return this._markFbElement();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Sets the correct dataAttributes on the facebook iframe and refreshes it.
     *
     * @see this.selectClass for parameters
     */
    _markFbElement: function () {
        return this._checkURL().then(() => {
            // Managing height based on options
            if (this.fbData.tabs) {
                this.fbData.height = this.fbData.tabs === 'events' ? 300 : 500;
            } else if (this.fbData.small_header) {
                this.fbData.height = 70;
            } else {
                this.fbData.height = 150;
            }
            _.each(this.fbData, (value, key) => {
                this.$target[0].dataset[key] = value;
            });
        });
    },
    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        const optionName = params.optionName;
        switch (methodName) {
            case 'toggleOption': {
                if (optionName.startsWith('tab.')) {
                    return this.fbData.tabs.split(',').includes(optionName.replace(/^tab./, ''));
                } else {
                    if (optionName === 'show_cover') {
                        // Sometimes a string, sometimes a boolean.
                        return String(this.fbData.hide_cover) === "false";
                    }
                    return this.fbData[optionName];
                }
            }
            case 'pageUrl': {
                return this._checkURL().then(() => this.fbData.href);
            }
        }
        return this._super(...arguments);
    },
    /**
     * @private
     */
    _checkURL: function () {
        const defaultURL = 'https://www.facebook.com/Odoo';
        // Patterns matched by the regex (all relate to existing pages,
        // in spite of the URLs containing "profile.php" or "people"):
        // - https://www.facebook.com/<pagewithaname>
        // - http://www.facebook.com/<page.with.a.name>
        // - www.facebook.com/<fbid>
        // - facebook.com/profile.php?id=<fbid>
        // - www.facebook.com/<name>-<fbid>  - NB: the name doesn't matter
        // - www.fb.com/people/<name>/<fbid>  - same
        // - m.facebook.com/p/<name>-<fbid>  - same
        // The regex is kept as a huge one-liner for performance as it is
        // compiled once on script load. The only way to split it on several
        // lines is with the RegExp constructor, which is compiled on runtime.
        const match = this.fbData.href.trim().match(/^(https?:\/\/)?((www\.)?(fb|facebook)|(m\.)?facebook)\.com\/(((profile\.php\?id=|people\/([^/?#]+\/)?|(p\/)?[^/?#]+-)(?<id>[0-9]{12,16}))|(?<nameid>[\w.]+))($|[/?# ])/);
        if (match) {
            // Check if the page exists on Facebook or not
            const pageId = match.groups.nameid || match.groups.id;
            return fetch(`https://graph.facebook.com/${pageId}/picture`)
            .then((res) => {
                if (res.ok) {
                    this.fbData.id = pageId;
                } else {
                    this.fbData.id = "";
                    this.fbData.href = defaultURL;
                    this.displayNotification({
                        title: _t("We couldn't find the Facebook page"),
                        type: "warning",
                    });
                }
            });
        }
        this.fbData.id = "";
        this.fbData.href = defaultURL;
        this.displayNotification({
            title: _t("You didn't provide a valid Facebook link"),
            type: "warning",
        });
        return Promise.resolve();
    },
});
});
