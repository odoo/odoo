/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insert } from '@mail/model/model_field_command';

registerModel({
    name: 'Visitor',
    modelMethods: {
        convertData(data) {
            const data2 = {};
            if ('country_id' in data) {
                if (data.country_id) {
                    data2.serverCountry = insert({
                        id: data.country_id,
                        code: data.country_code,
                    });
                } else {
                    data2.serverCountry = clear();
                }
            }
            if ('history' in data) {
                data2.history = data.history;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('is_connected' in data) {
                data2.is_connected = data.is_connected;
            }
            if ('lang_name' in data) {
                data2.lang_name = data.lang_name;
            }
            if ('display_name' in data) {
                data2.display_name = data.display_name;
            }
            if ('partner_id' in data) {
                if (data.partner_id) {
                    data2.partner = insert({ id: data.partner_id });
                } else {
                    data2.partner = clear();
                }
            }
            if ('website_name' in data) {
                data2.website_name = data.website_name;
            }
            return data2;
        },
    },
    fields: {
        /**
         * Url to the avatar of the visitor.
         */
        avatarUrl: attr({
            compute() {
                if (!this.partner) {
                    return '/mail/static/src/img/smiley/avatar.jpg';
                }
                return this.partner.avatarUrl;
            },
        }),
        /**
         * Country of the visitor.
         */
        country: one('Country', {
            compute() {
                if (this.partner && this.partner.country) {
                    return this.partner.country;
                }
                if (this.serverCountry) {
                    return this.serverCountry;
                }
                return clear();
            },
        }),
        /**
         * Display name of the visitor.
         */
        display_name: attr(),
        /**
         * Browsing history of the visitor as a string.
         */
        history: attr(),
        /**
         * States the id of this visitor.
         */
        id: attr({
            identifying: true,
        }),
        /**
         * Determine whether the visitor is connected or not.
         */
        is_connected: attr(),
        /**
         * Name of the language of the visitor. (Ex: "English")
         */
        lang_name: attr(),
        nameOrDisplayName: attr({
            compute() {
                if (this.partner) {
                    return this.partner.nameOrDisplayName;
                }
                return this.display_name;
            },
        }),
        /**
         * Partner linked to this visitor, if any.
         */
        partner: one('Partner'),
        serverCountry: one('Country'),
        /**
         * Threads with this visitor as member
         */
        threads: many('Thread', {
            inverse: 'visitor',
        }),
        /**
         * Name of the website on which the visitor is connected. (Ex: "Website 1")
         */
        website_name: attr(),
    },
});
