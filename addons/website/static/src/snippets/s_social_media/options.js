/** @odoo-module **/

import fonts from 'wysiwyg.fonts';
import {generateHTMLId} from 'web_editor.utils';
import options from 'web_editor.snippets.options';

options.registry.SocialMedia = options.Class.extend({
    /**
     * @override
     */
    async willStart() {
        this.$target[0].querySelectorAll(':scope > a').forEach(el => el.setAttribute('id', generateHTMLId(30)));
        await this._super(...arguments);
        let websiteId;
        this.trigger_up('context_get', {
            callback: function (ctx) {
                websiteId = ctx['website_id'];
            },
        });
        // Fetch URLs for db links.
        [this.dbSocialValues] = await this._rpc({
            model: 'website',
            method: 'read',
            args: [websiteId, ['social_facebook', 'social_twitter', 'social_youtube',
                'social_instagram', 'social_linkedin', 'social_github']],
        });
        delete this.dbSocialValues.id;
    },
    /**
     * @override
     */
    async cleanForSave() {
        this.$target[0].querySelectorAll(':scope > a').forEach(el => el.removeAttribute('id'));
        // Update the DB links.
        let websiteId;
        this.trigger_up('context_get', {
            callback: function (ctx) {
                websiteId = ctx['website_id'];
            },
        });
        await this._rpc({
            model: 'website',
            method: 'write',
            args: [[websiteId], this.dbSocialValues],
        });
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
        const entries = JSON.parse(widgetValue);
        // Handle element deletation.
        const entriesIds = entries.map(entry => entry.id);
        const anchorsEls = this.$target[0].querySelectorAll(':scope > a');
        const deletedEl = Array.from(anchorsEls).find(aEl => !entriesIds.includes(aEl.id));
        if (deletedEl) {
            deletedEl.remove();
        }
        for (const entry of entries) {
            let anchorEl = this.$target[0].querySelector(`#${entry.id}`);
            if (!anchorEl) {
                // It's a new social media.
                anchorEl = this.$target[0].querySelector(':scope > a').cloneNode(true);
                anchorEl.href = '#';
                anchorEl.setAttribute('id', entry.id);
            }
            // Handle visibility of the link
            anchorEl.classList.toggle('d-none', !entry.selected);

            const dbField = anchorEl.href.split('/website/social/')[1];
            if (dbField) {
                // Handle URL change for DB links.
                this.dbSocialValues['social_' + dbField] = entry.display_name;
            } else {
                // Handle URL change for custom links.
                const href = anchorEl.getAttribute('href');
                if (href !== entry.display_name) {
                    if (this._isValidURL(entry.display_name)) {
                        // Propose an icon only for valid URLs (no mailto).
                        const socialMedia = this._findRelevantSocialMedia(entry.display_name);

                        // Remove social media social media classes
                        let regx = new RegExp('\\b' + "s_social_media_" + '[^1-9][^ ]*[ ]?\\b', 'g');
                        anchorEl.className = anchorEl.className.replace(regx, '');

                        // Remove every fa classes except fa-x sizes
                        const iEl = anchorEl.querySelector('i');
                        regx = new RegExp('\\b' + "fa-" + '[^1-9][^ ]*[ ]?\\b', 'g');
                        iEl.className = iEl.className.replace(regx, '');

                        if (socialMedia) {
                            anchorEl.classList.add(`s_social_media_${socialMedia}`);
                            iEl.classList.add(`fa-${socialMedia}`);
                        } else {
                            iEl.classList.add(`fa-pencil`);
                        }
                    }
                    anchorEl.setAttribute('href', entry.display_name);
                }
            }
            // Place the link at the correct position
            this.$target[0].appendChild(anchorEl);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName !== 'renderListItems') {
            return this._super(methodName, params);
        }
        const listEntries = [];
        for (const anchorEl of this.$target[0].querySelectorAll(':scope > a')) {
            const dbField = anchorEl.href.split('/website/social/')[1];
            const entry = {
                id: anchorEl.id,
                selected: !anchorEl.classList.contains('d-none'),
                display_name: dbField ? this.dbSocialValues['social_' + dbField] : anchorEl.getAttribute('href'),
                undeletable: Boolean(dbField),
                placeholder: `https://${dbField || 'example'}.com/yourPage`,
            };
            listEntries.push(entry);
        }
        return JSON.stringify(listEntries);
    },
    /**
     * Finds the social network for the given url.
     *
     * @param  {String} url
     * @return {String} The social network to which the url leads to.
     */
    _findRelevantSocialMedia(url) {
        const supportedSocialMedia = [
            ['facebook', /^(https?:\/\/)(www\.)?(facebook|fb|m\.facebook)\.(com|me)\/.+$/gm],
            ['twitter', /^(https?:\/\/)((www\.)?twitter\.com)\/.+$/gm],
            ['youtube', /^(https?:\/\/)(www\.)?(youtube.com|youtu.be)\/.+$/gm],
            ['instagram', /^(https?:\/\/)(www\.)?(instagram.com|instagr.am|instagr.com)\/.+$/gm],
            ['linkedin', /^(https?:\/\/)((www\.)?linkedin\.com)\/.+$/gm],
            ['github', /^(https?:\/\/)((www\.)?github\.com)\/.+$/gm],
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
            return fonts.fontIcons[0].alias.find(el => el.includes(domain)).split('fa-').pop();
        } catch (error) {
            return false;
        }
    },
    /**
     * @param  {String} str
     * @returns {boolean} is the string a valid URL.
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
     * @override
     */
    _renderCustomXML(uiFragment) {
        const anchorEls = this.$target[0].querySelectorAll(':scope > a:not(.d-none)');
        uiFragment.querySelector('we-list').dataset.defaults = JSON.stringify(
            Array.from(anchorEls).map(el => el.id)
        );
    }
});

export default {
    SocialMedia: options.registry.SocialMedia,
};
