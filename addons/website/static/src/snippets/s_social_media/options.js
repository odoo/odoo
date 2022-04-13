/** @odoo-module **/

import options from 'web_editor.snippets.options';
import {SocialMedia} from '@web_editor/js/editor/snippets/s_social_media/options'

let dbSocialValues;
let dbSocialValuesProm;
export const clearDbSocialValuesCache = () => {
    dbSocialValuesProm = undefined;
    dbSocialValues = undefined;
};
options.registry.SocialMediaWebsite = SocialMedia.extend({
    /**
     * @override
     */
    async cleanForSave() {
        // Update the DB links.
        let websiteId;
        this.trigger_up('context_get', {
            callback: function (ctx) {
                websiteId = ctx['website_id'];
            },
        });
        const fields = {};
        for (const [mediaName, url] of Object.entries(dbSocialValues)) {
            fields["social_" + mediaName] = url;
        }
        await this._rpc({
            model: 'website',
            method: 'write',
            args: [[websiteId], fields],
        });
    },


    //--------------------------------------------------------------------------
    // Private
    //-------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const _super = this._super.bind(this);
        if (methodName === 'renderListItems') {
            await this._fetchSocialMedia();
        }
        const result = _super(methodName, params);
        for (const entry of this._lastEntries) {
            if (entry.media) {
                dbSocialValues[entry.media] = entry.display_name;
            }
        }
        return result;
    },

    /**
     * @override
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
            dbSocialValuesProm = this._rpc({
                model: 'website',
                method: 'read',
                args: [websiteId, ['social_facebook', 'social_twitter', 'social_linkedin',
                    'social_youtube', 'social_instagram', 'social_github']],
            }).then(([values]) => {
                delete values.id;
                dbSocialValues = {};
                for (const [name, url] of Object.entries(values)) {
                    dbSocialValues[name.split('social_')[1]] = url;
                }
            });
        }
        await dbSocialValuesProm;
    },
    /**
     * @override
     */
    async _getStickyMedias() {
        await this._fetchSocialMedia();
        return {...dbSocialValues};
    },
    _getInternalMediaName(url) {
        return url.split('/website/social/')[1];
    },
    /**
     * @override
     */
    async _getDisplayName(url) {
        const mediaName = this._getInternalMediaName(url);
        const medias = await this._getStickyMedias();
        return mediaName ? medias[mediaName] : url;
    },
    /**
     * @override
     */
    _getEntrySavedUrl(entry) {
        return entry.media ? `/website/social/${entry.media}`: entry.display_name;
    },
    /**
     * @override
     */
    _createIconElement() {
        const faEl = document.createElement('i');
        faEl.classList.add('fa', 'fa-pencil','rounded-circle', 'shadow-sm');
        return faEl;
    },
});
