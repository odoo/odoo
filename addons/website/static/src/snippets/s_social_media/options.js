/** @odoo-module **/

import fonts from '@web_editor/js/wysiwyg/fonts';
import weUtils from '@web_editor/js/common/utils';
import options from '@web_editor/js/editor/snippets.options';
import { _t } from "@web/core/l10n/translation";

let dbSocialValues;
let dbSocialValuesProm;
const clearDbSocialValuesCache = () => {
    dbSocialValuesProm = undefined;
    dbSocialValues = undefined;
};
const getDbSocialValuesCache = () => {
    return dbSocialValues;
};

options.registry.SocialMedia = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @override
     */
    start() {
        // When the alert is clicked, focus the first media input in the editor.
        this.__onSetupBannerClick = this._onSetupBannerClick.bind(this);
        this.$target[0].addEventListener('click', this.__onSetupBannerClick);
        this.entriesNotInDom = [];
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async onBuilt() {
        await this._fetchSocialMedia();
        for (const anchorEl of this.$target[0].querySelectorAll(':scope > a')) {
            const mediaName = anchorEl.href.split('/website/social/').pop();
            if (mediaName && !dbSocialValues[`social_${mediaName}`]) {
                // Delete social media without value in DB.
                anchorEl.remove();
            }
        }
        // Ensure we do not drop a blank block.
        this._handleNoMediaAlert();
    },
    /**
     * @override
     */
    async cleanForSave() {
        // When the snippet is cloned via its parent, the options UI won't be
        // updated and DB values won't be fetched, the options `cleanForSave`
        // will then update the website with empty values.
        if (!dbSocialValues) {
            return;
        }
        // Update the DB links.
        let websiteId;
        this.trigger_up('context_get', {
            callback: function (ctx) {
                websiteId = ctx['website_id'];
            },
        });
        await this.orm.write("website", [websiteId], dbSocialValues);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.$target[0].removeEventListener('click', this.__onSetupBannerClick);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Applies the we-list on the target and rebuilds the social links.
     *
     * @see this.selectClass for parameters
     */
    async renderListItems(previewMode, widgetValue, params) {
        const anchorEls = this.$target[0].querySelectorAll(':scope > a');
        let entries = JSON.parse(widgetValue);
        const anchorsToRemoveEls = [];
        for (let i = 0; i < anchorEls.length; i++) {
            // For each position, check if the item that was there before
            // (marked by _computeWidgetState), is still there. Otherwise,
            // remove it. TODO improve ?
            if (!entries.find(entry => parseInt(entry.domPosition) === i)) {
                anchorsToRemoveEls.push(anchorEls[i]);
            }
        }
        for (const el of anchorsToRemoveEls) {
            el.remove();
        }
        this.entriesNotInDom = [];

        for (let listPosition = 0; listPosition < entries.length; listPosition++) {
            const entry = entries[listPosition];
            // Check if the url is valid.
            const url = entry.display_name;
            if (url && !/^(([a-zA-Z]+):|\/)/.test(url)) {
                // We permit every protocol (http:, https:, ftp:, mailto:,...).
                // If none is explicitly specified, we assume it is a https.
                entry.display_name = `https://${url}`;
            }
            const isDbField = Boolean(entry.media);
            if (isDbField) {
                // Handle URL change for DB links.
                dbSocialValues[`social_${entry.media}`] = entry.display_name;
            }

            let anchorEl = anchorEls[entry.domPosition];
            if (entry.selected) {
                if (!anchorEl) {
                    if (anchorEls.length === 0) {
                        // Create a HTML element if no one already exist.
                        anchorEl = document.createElement('a');
                        anchorEl.setAttribute('target', '_blank');
                        const iEl = document.createElement('i');
                        iEl.classList.add('fa', 'rounded-circle', 'shadow-sm', 'o_editable_media');
                        anchorEl.appendChild(iEl);
                    } else {
                        // Copy existing style if there is already another link.
                        anchorEl = this.$target[0].querySelector(':scope > a').cloneNode(true);
                        this._removeSocialMediaClasses(anchorEl);
                    }
                    const faIcon = isDbField ? `fa-${entry.media}` : 'fa-pencil';
                    anchorEl.querySelector('i').classList.add(faIcon);
                    if (isDbField) {
                        anchorEl.href = `/website/social/${encodeURIComponent(entry.media)}`;
                        anchorEl.classList.add(`s_social_media_${entry.media}`);
                    }
                }
            } else {
                if (anchorEl) {
                    delete entry.domPosition;
                    anchorEl.remove();
                }
                entry.listPosition = listPosition;
                this.entriesNotInDom.push(entry);
                continue;
            }
            if (!isDbField) {
                // Handle URL change for custom links.
                const href = anchorEl.getAttribute('href');
                if (href !== entry.display_name) {
                    if (this._isValidURL(entry.display_name)) {
                        // Propose an icon only for valid URLs (no mailto).
                        const socialMedia = this._findRelevantSocialMedia(entry.display_name);
                        if (socialMedia) {
                            const iEl = anchorEl.querySelector('i');
                            this._removeSocialMediaClasses(anchorEl);
                            anchorEl.classList.add(`s_social_media_${socialMedia}`);
                            iEl.classList.add(`fa-${socialMedia}`);
                        }
                    }
                    anchorEl.setAttribute('href', entry.display_name);
                }
            }
            // Place the link at the correct position
            this.$target[0].appendChild(anchorEl);
        }

        // Restore whitespaces around the links
        this.$target[0].normalize();
        const finalLinkEls = this.$target[0].querySelectorAll(':scope > a');
        if (finalLinkEls.length) {
            finalLinkEls[0].previousSibling.textContent = '\n';
            for (const linkEl of finalLinkEls) {
                linkEl.after(document.createTextNode('\n'));
            }
        }

        this._handleNoMediaAlert();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName !== 'renderListItems') {
            return this._super(methodName, params);
        }
        await this._fetchSocialMedia();
        let listPosition = 0;
        let domPosition = 0;
        // Check the DOM to compute the state of the ListUserValueWidget.
        let entries = [...this.$target[0].querySelectorAll(':scope > a')].map(el => {
            const media = el.href.split('/website/social/')[1];
            // Avoid a DOM entry and a non-dom entry having the same position.
            while (this.entriesNotInDom.find(entry => entry.listPosition === listPosition)) {
                listPosition++;
            }
            return {
                id: weUtils.generateHTMLId(),
                display_name: media ? dbSocialValues[`social_${media}`] : el.getAttribute('href'),
                placeholder: `https://${encodeURIComponent(media) || 'example'}.com/yourPage`,
                undeletable: !!media,
                notToggleable: !media,
                selected: true,
                listPosition: listPosition++,
                domPosition: domPosition++,
                media: media,
            };
        });
        // Adds the DB social media links that are not in the DOM.
        for (let [media, link] of Object.entries(dbSocialValues)) {
            media = media.split('social_').pop();
            if (!this.$target[0].querySelector(`:scope > a[href="/website/social/${encodeURIComponent(media)}"]`)) {
                const entryNotInDom = this.entriesNotInDom.find(entry => entry.media === media);
                if (!entryNotInDom) {
                    this.entriesNotInDom.push({
                        id: weUtils.generateHTMLId(),
                        display_name: link,
                        placeholder: `https://${encodeURIComponent(media)}.com/yourPage`,
                        undeletable: true,
                        selected: false,
                        listPosition: listPosition++,
                        media: media,
                        notToggleable: false,
                    });
                } else {
                    // Do not change the listPosition of the existing entry.
                    entryNotInDom.display_name = link;
                    entryNotInDom.undeletable = true;
                    entryNotInDom.notToggleable = false;
                }
            }
        }
        // Reorder entries and entriesNotInDom by position.
        entries = entries.concat(this.entriesNotInDom);
        entries.sort((a, b) => {
            return a.listPosition - b.listPosition;
        });
        return JSON.stringify(entries);
    },
    /**
     * Fetches the urls of the social networks that are in the database.
     */
    async _fetchSocialMedia() {
        if (!dbSocialValuesProm) {
            let websiteId;
            this.trigger_up('context_get', {
                callback: function (ctx) {
                    websiteId = ctx['website_id'];
                },
            });
            // Fetch URLs for db links.
            dbSocialValuesProm = this.orm.read("website", [websiteId], [
                "social_facebook",
                "social_twitter",
                "social_linkedin",
                "social_youtube",
                "social_instagram",
                "social_github",
                "social_tiktok",
            ]).then(function (values) {
                [dbSocialValues] = values;
                delete dbSocialValues.id;
            });
        }
        await dbSocialValuesProm;
    },
    /**
     * Finds the social network for the given url.
     *
     * @param {String} url
     * @return {String} The social network to which the url leads to.
     */
    _findRelevantSocialMedia(url) {
        // Note that linkedin, twitter, github and tiktok will also work because
        // the url will match the good icon so we don't need a specific regex.
        const supportedSocialMedia = [
            ['facebook', /^(https?:\/\/)(www\.)?(facebook|fb|m\.facebook)\.(com|me).*$/],
            ['youtube', /^(https?:\/\/)(www\.)?(youtube.com|youtu.be).*$/],
            ['instagram', /^(https?:\/\/)(www\.)?(instagram.com|instagr.am|instagr.com).*$/],
        ];
        for (const [socialMedia, regex] of supportedSocialMedia) {
            if (regex.test(url)) {
                return socialMedia;
            }
        }
        // Check if an icon matches the URL domain
        try {
            const domain = new URL(url).hostname.split('.').slice(-2)[0];
            fonts.computeFonts();
            const iconNames = fonts.fontIcons[0].alias;
            const exactIcon = iconNames.find(el => el === `fa-${domain}`);
            return (exactIcon || iconNames.find(el => el.includes(domain))).split('fa-').pop();
        } catch {
            return false;
        }
    },
    /**
     * Adds a warning banner to alert that there are no social networks.
     */
    _handleNoMediaAlert() {
        const alertEl = this.$target[0].querySelector('div.css_non_editable_mode_hidden');
        if (this.$target[0].querySelector(':scope > a:not(.d-none)')) {
            if (alertEl) {
                alertEl.remove();
            }
        } else {
            if (!alertEl) {
                // Create the alert banner.
                const divEl = document.createElement('div');
                const classes = ['alert', 'alert-info', 'css_non_editable_mode_hidden', 'text-center'];
                divEl.classList.add(...classes);
                const spanEl = document.createElement('span');
                spanEl.textContent = _t("Click here to setup your social networks");
                this.$target[0].appendChild(divEl).append(spanEl);
            }
        }
    },
    /**
     * @param  {String} str
     * @returns {boolean} is the string a valid URL.
     */
    _isValidURL(str) {
        let url;
        try {
            url = new URL(str);
        } catch {
            return false;
        }
        return url.protocol.startsWith('http');
    },
    /**
     * Removes social media classes from the given element.
     *
     * @param  {HTMLElement} anchorEl
     */
    _removeSocialMediaClasses(anchorEl) {
        let regx = new RegExp('\\b' + 's_social_media_' + '[^1-9][^ ]*[ ]?\\b');
        anchorEl.className = anchorEl.className.replace(regx, '');
        const iEl = anchorEl.querySelector('i');
        regx = new RegExp('\\b' + 'fa-' + '[^1-9][^ ]*[ ]?\\b');
        // Remove every fa classes except fa-x sizes.
        iEl.className = iEl.className.replace(regx, '');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onSetupBannerClick(ev) {
        if (ev.target.closest('div.css_non_editable_mode_hidden')) {
            // TODO if the options are not already instantiated, this won't
            // work of course
            this._requestUserValueWidgets('social_media_list')[0].focus();
        }
    },
});

export default {
    SocialMedia: options.registry.SocialMedia,
    clearDbSocialValuesCache,
    getDbSocialValuesCache,
};
