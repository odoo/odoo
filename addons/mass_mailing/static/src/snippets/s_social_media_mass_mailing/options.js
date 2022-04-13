odoo.define('@web_editor/src/snippets/s_social_media_mass_mailing/options', function (require) {

const options = require('web_editor.snippets.options');
const {SocialMedia} = require('@web_editor/js/editor/snippets/s_social_media/options');
const rpc = require('web.rpc');
const session = require('web.session');

const getCurrentCompanyId = () => session.user_context.allowed_company_ids[0];

let dbSocialValues;
let dbSocialValuesProm;
options.registry.SocialMediaMassMailing = SocialMedia.extend({
    /**
     * @override
     */
    async cleanForSave() {
        await this._super.apply(this, arguments);
        // Ensure dbSocialValues are loaded.
        await this._fetchSocialMedia();
        const dbSocialFieldsToSave = new Set();
        for (const [mediaName, url] of Object.entries(dbSocialValues)) {
            if (!url) {
                dbSocialFieldsToSave.add(mediaName);
            }
        }
        // Fill the res.company fields that will be updated in the database only
        // for the fields are currently empty.
        const dbSocialValuesToSave = {};
        for (const entry of this._lastEntries) {
            if (entry.media && entry.display_name && dbSocialFieldsToSave.has(entry.media)) {
                dbSocialValues[entry.media] = entry.display_name;
                dbSocialValuesToSave[`social_${entry.media}`] = entry.display_name;
                dbSocialFieldsToSave.delete(entry.media);
            }
        }

        // Use the `session.rpc` instead of `this._rpc` to prevent a traceback
        // error popup to showup.
        const query = rpc.buildQuery({
            model: 'res.company',
            method: 'write',
            args: [[getCurrentCompanyId()], dbSocialValuesToSave],
        });
        await session.rpc(query.route, query.params).catch(e => {
            if (e.message.exceptionName !== 'odoo.exceptions.AccessError') {
                return Promise.reject(e);
            }
        });
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    editCompanySocial(previewMode, widgetValue, params) {
        if (previewMode !== false) {
            return;
        }
        this.do_action({
            res_id: getCurrentCompanyId(),
            res_model: "res.company",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _fetchSocialMedia() {
        if (!dbSocialValuesProm) {
            dbSocialValuesProm = this._rpc({
                model: 'res.company',
                method: 'read',
                args: [[getCurrentCompanyId()], ['social_facebook', 'social_twitter', 'social_linkedin',
                    'social_youtube', 'social_instagram', 'social_github']],
            }).then(([values]) => {
                delete values.id;
                dbSocialValues = {};
                for (const [name, url] of Object.entries(values)) {
                    dbSocialValues[name.split('social_')[1]] = url;
                }
            });
        }
        return dbSocialValuesProm;
    },
    /**
     * @override
     */
    async _getStickyMedias() {
        await this._fetchSocialMedia();
        return {...dbSocialValues};
    },
    /**
     * @override
     */
    _normalizeNodes() {
        this._super(...arguments);
        for (const node of this.$target[0].childNodes) {
            if (node.nodeType === Node.TEXT_NODE) {
                node.textContent = '\xa0\xa0 ';
            }
        }
        for (const node of this.$target[0].querySelectorAll(':scope > a')) {
            node.style["margin-left"] = "10px";
        }
    },
});

});
