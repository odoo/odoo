odoo.define('website_livechat/static/src/models/partner/partner.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class Visitor extends dependencies['mail.model'] {
        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static convertData(data) {
            const data2 = {};
            if ('country_id' in data) {
                if (data.country_id) {
                    data2.country = [['insert', {
                        id: data.country_id,
                        code: data.country_code,
                    }]];
                } else {
                    data2.country = [['unlink']];
                }
            }
            if ('history' in data) {
                data2.history = data.history;
            }
            if ('is_connected' in data) {
                data2.is_connected = data.is_connected;
            }
<<<<<<< HEAD
            if ('lang' in data) {
                data2.lang = data.lang;
            }
            if ('name' in data) {
                data2.name = data.name;
=======
            if ('lang_name' in data) {
                data2.lang_name = data.lang_name;
            }
            if ('display_name' in data) {
                data2.display_name = data.display_name;
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
            }
            if ('partner_id' in data) {
                if (data.partner_id) {
                    data2.partner = [['insert', { id: data.partner_id }]];
                } else {
                    data2.partner = [['unlink']];
                }
            }
<<<<<<< HEAD
            if ('website' in data) {
                data2.website = data.website;
=======
            if ('website_name' in data) {
                data2.website_name = data.website_name;
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
            }
            return data2;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            if (!this.partner) {
                return '/mail/static/src/img/smiley/avatar.jpg';
            }
            return this.partner.avatarUrl;
        }

        /**
         * @private
         * @returns {mail.country}
         */
        _computeCountry() {
            if (this.partner && this.partner.country) {
                return [['link', this.partner.country]];
            }
            if (this.country) {
                return [['link', this.country]];
            }
            return [['unlink']];
        }

        /**
         * @private
         * @returns {string}
         */
        _computeNameOrDisplayName() {
            if (this.partner) {
                return this.partner.nameOrDisplayName;
            }
<<<<<<< HEAD
            return this.name;
=======
            return this.display_name;
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
        }
    }

    Visitor.fields = {
        /**
         * Url to the avatar of the visitor.
         */
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
            dependencies: [
                'partner',
                'partnerAvatarUrl',
            ],
        }),
        /**
         * Country of the visitor.
         */
        country: many2one('mail.country', {
            compute: '_computeCountry',
            dependencies: [
                'country',
                'partnerCountry',
            ],
        }),
        /**
<<<<<<< HEAD
=======
         * Display name of the visitor.
         */
        display_name: attr(),
        /**
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
         * Browsing history of the visitor as a string.
         */
        history: attr(),
        /**
         * Determine whether the visitor is connected or not.
         */
        is_connected: attr(),
        /**
         * Name of the language of the visitor. (Ex: "English")
         */
<<<<<<< HEAD
        lang: attr(),
        /**
         * Name of the visitor.
         */
        name: attr(),
        nameOrDisplayName: attr({
            compute: '_computeNameOrDisplayName',
            dependencies: [
                'name',
=======
        lang_name: attr(),
        nameOrDisplayName: attr({
            compute: '_computeNameOrDisplayName',
            dependencies: [
                'display_name',
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
                'partnerNameOrDisplayName',
            ],
        }),
        /**
         * Partner linked to this visitor, if any.
         */
        partner: many2one('mail.partner'),
        partnerAvatarUrl: attr({
            related: 'partner.avatarUrl',
        }),
        partnerCountry: many2one('mail.country',{
            related: 'partner.country',
        }),
        partnerNameOrDisplayName: attr({related: 'partner.nameOrDisplayName'}),
        /**
         * Threads with this visitor as member
         */
        threads: one2many('mail.thread', {
            inverse: 'visitor',
        }),
        /**
         * Name of the website on which the visitor is connected. (Ex: "Website 1")
         */
<<<<<<< HEAD
        website: attr(),
=======
        website_name: attr(),
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
    };

    Visitor.modelName = 'website_livechat.visitor';

    return Visitor;
}

registerNewModel('website_livechat.visitor', factory);

});
