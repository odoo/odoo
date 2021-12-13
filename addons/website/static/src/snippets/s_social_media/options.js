/** @odoo-module **/

import {_t} from 'web.core';
import options from 'web_editor.snippets.options';

const dbData = {
    'social_facebook': undefined,
    'social_twitter': undefined,
    'social_instagram': undefined,
    'social_youtube': undefined,
    'social_linkedin': undefined,
    'social_github': undefined,
};
const dbFieldByUrl = {
    '/website/social/facebook': 'social_facebook',
    '/website/social/twitter': 'social_twitter',
    '/website/social/youtube': 'social_youtube',
    '/website/social/instagram': 'social_instagram',
    '/website/social/linkedin': 'social_linkedin',
    '/website/social/github': 'social_github',
};
const localUrlByDbField = _.invert(dbFieldByUrl);

options.registry.SocialMedia = options.Class.extend({
    /**
     * @override
     */
    async start() {
        if (dbData['social_facebook'] === undefined) {
            // Fetch URLs for db links.
            await this._rpc({
                model: 'website',
                method: 'search_read',
                args: [[], Object.keys(dbData)],
                limit: 1,
            }).then(function (res) {
                if (res) {
                    delete res[0].id;
                    for (let key in res[0]) {
                        dbData[key] = res[0][key];
                    }
                }
            });
        }
    },
    /**
     * @override
     */
    async cleanForSave() {
        // Fetch the website id.
        let websiteId;
        await this.trigger_up('context_get', {
            callback: (ctx) => {
                websiteId = ctx['website_id'];
            },
        });
        // Do a RPC to update the DB links.
        this._rpc({
            model: 'website',
            method: 'write',
            args: [
                [websiteId],
                {
                    ['social_facebook']: dbData['social_facebook'],
                    ['social_twitter']: dbData['social_twitter'],
                    ['social_youtube']: dbData['social_youtube'],
                    ['social_instagram']: dbData['social_instagram'],
                    ['social_linkedin']: dbData['social_linkedin'],
                    ['social_github']: dbData['social_github'],
                }
            ],
        });
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Apply the we-list on the target.
     */
    async renderListItems(previewMode, value) {
        const entries = JSON.parse(value);
        const anchorsEls = this.$target[0].querySelectorAll('a[data-social-id]');
        // Handle element deletation.
        const ids = entries.map(entry => entry.id);
        const deletedAEl = Array.from(anchorsEls).find(aEl => !ids.includes(aEl.dataset.socialId));
        if (deletedAEl) {
            deletedAEl.remove();
        }

        for (let i = 0; i < entries.length; i++) {
            const entry = entries[i];
            let anchorEl = this.$target[0].querySelector(`[data-social-id="${entry.id}"]`);
            if (!anchorEl) {
                let iEl;
                if (!this.$target[0].querySelector('a')) {
                    // Create a link with default style.
                    iEl = document.createElement('i');
                    iEl.setAttribute('class', 'fa rounded shadow-sm');
                    anchorEl = document.createElement('a');
                    anchorEl.setAttribute('target', '_blank');
                    anchorEl.appendChild(iEl);
                } else {
                    // Create a link that has the same style as the others.
                    anchorEl = this.$target[0].querySelector('a').cloneNode(true);
                }
                anchorEl.dataset.socialId = entry.id;
            }
            // Handle visibility of the link
            anchorEl.classList.toggle('d-none', !entry.selected);
            if (entry.id in localUrlByDbField) {
                // Handle URL change for DB links.
                dbData[entry.id] = entry.display_name;
            } else {
                // Handle URL change for custom links.
                const href = anchorEl.getAttribute('href');
                if (href !== entry.display_name) {
                    if (this._isValidURL(entry.display_name)) {
                        // Propose an icon only for valid URLs (no mailto).
                        const socialMedia = this._findRelevantSocialMedia(entry.display_name);
                        this._removeSocialMediaClasses(anchorEl);
                        const iEl = anchorEl.querySelector('i');
                        this._removeSocialMediaClasses(iEl);
                        if (socialMedia) {
                            anchorEl.classList.add(`s_share_${socialMedia}`);
                            iEl.classList.add(`fa-${socialMedia}`);
                        } else {
                            iEl.classList.add(`fa-pencil`);
                        }
                    }
                    anchorEl.setAttribute('href', entry.display_name);
                }
            }
            // Place the link at the correct position
            this.$target[0].insertAdjacentElement('beforeend', anchorEl);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Calculates a similarity score between two strings.
     * 
     * @param  {String} s1
     * @param  {String} s2
     */
    _compareStrings(s1, s2) {
        let longer = s1;
        let shorter = s2;
        if (s1.length < s2.length) {
            longer = s2;
            shorter = s1;
        }
        const longerLength = longer.length;
        if (longerLength === 0) {
            return 1.0;
        }
        return (longerLength - this._editDistance(longer, shorter)) / parseFloat(longerLength);
    },
    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName !== 'renderListItems') {
            return this._super(methodName, params);
        }
        const listEntries = [];
        const anchorsEls = this.$target[0].querySelectorAll('a');
        for (let i = 0; i < anchorsEls.length; i++) {
            const anchorEl = anchorsEls[i];
            const href = anchorEl.getAttribute('href');
            if (dbFieldByUrl[href]) {
                // It's a DB social link
                listEntries.push({
                    id: _t(dbFieldByUrl[href]),
                    display_name: _t(dbData[dbFieldByUrl[href]]),
                    undeletable: true,
                    selected: !anchorEl.classList.contains('d-none'),
                });
            } else {
                // It's a custom social link.
                listEntries.push({
                    id: _t(anchorEl.dataset.socialId),
                    display_name: _t(href),
                    undeletable: false,
                    selected: !anchorEl.classList.contains('d-none'),
                });
            }
        }
        return JSON.stringify(listEntries);
    },
    /**
     * Calculates the number of changes (insertions, deletions or substitutions)
     * needed to go from s1 to s2.
     * 
     * @see https://en.wikipedia.org/wiki/Levenshtein_distance
     * @param  {String} s1
     * @param  {String} s2
     */
    _editDistance(s1, s2) {
        s1 = s1.toLowerCase();
        s2 = s2.toLowerCase();
        const costs = new Array();
        for (let i = 0; i <= s1.length; i++) {
            let lastValue = i;
            for (let j = 0; j <= s2.length; j++) {
                if (i === 0) {
                    costs[j] = j;
                } else {
                    if (j > 0) {
                        let newValue = costs[j - 1];
                        if (s1.charAt(i - 1) !== s2.charAt(j - 1)) {
                            newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                        }
                        costs[j - 1] = lastValue;
                        lastValue = newValue;
                    }
                }
            }
            if (i > 0) {
                costs[s2.length] = lastValue;
            }
        }
        return costs[s2.length];
    },
    /**
     * Finds the most relevant social network for the url given in parameter.
     * 
     * @param  {String} url
     * @return {String} The social network with the best similarity score.
     */
    _findRelevantSocialMedia(url) {
        const supportedSocialMedia =
            ['facebook', 'twitter', 'youtube', 'instagram', 'linkedin', 'github'];
        let moreAccurateSocialMedia = '';
        let scoreOfMoreAccurateSocialMedia = 0;
        // Extract base url.
        url = new URL(url);
        url = url.hostname.replace(/^www\./, '');
        for (let i = 0; i < supportedSocialMedia.length; i++) {
            const score = this._compareStrings(url, `${supportedSocialMedia[i]}.com`);
            if (score > scoreOfMoreAccurateSocialMedia) {
                scoreOfMoreAccurateSocialMedia = score;
                moreAccurateSocialMedia = supportedSocialMedia[i];
            }
        }
        if (scoreOfMoreAccurateSocialMedia > 0.58) {
            return moreAccurateSocialMedia;
        }
    },
    /**
     * Checks that the string is a valid URL.
     * 
     * @param  {String} str
     * @returns {boolean}
     */
    _isValidURL(str) {
        try {
            new URL(str);
        } catch (error) {
            return false;
        }
        return true;
    },
    /**
     * Removes the classes related to social networks (icons and colors).
     * 
     * @param  {HTMLElement} element
     */
    _removeSocialMediaClasses(element) {
        // Remove the social media classes.
        for (let i = 0; i < element.classList.length; i++) {
            const className = element.classList[i];
            if (className.startsWith('fa-') || className.startsWith('s_share_')) {
                element.classList.remove(className);
            }
        }
    },
    /**
     * @override
     * @param {HTMLElement} uiFragment
     */
    _renderCustomXML(uiFragment) {
        const listEl = uiFragment.querySelector('we-list');
        const socialIds = [];
        this.$target[0].querySelectorAll('a[data-social-id]').forEach(anchorEl => {
            if (!anchorEl.classList.contains('d-none')) {
                socialIds.push(anchorEl.dataset.socialId);
            }
        });
        listEl.dataset.defaults = JSON.stringify(socialIds);
    }
});

export default {
    SocialMedia: options.registry.SocialMedia,
};