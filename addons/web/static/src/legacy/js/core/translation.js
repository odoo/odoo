
/** @odoo-module alias=web.translation **/

import Class from "web.Class";
import { translatedTerms } from "@web/core/l10n/translation";

var TranslationDataBase = Class.extend(/** @lends instance.TranslationDataBase# */{
    init: function() {
        this.db = translatedTerms;
        this.multi_lang = false
        this.parameters = {"direction": 'ltr',
                        "date_format": '%m/%d/%Y',
                        "time_format": '%H:%M:%S',
                        "grouping": [],
                        "decimal_point": ".",
                        "thousands_sep": ",",
                        "code": "en_US"};
    },
    set_bundle: function(translation_bundle) {
        var self = this;
        this.multi_lang = translation_bundle.multi_lang
        var modules = Object.keys(translation_bundle.modules);
        modules.sort();
        if (modules.includes("web")) {
            modules = ["web"].concat(modules.filter((module) => module !== "web"));
        }
        modules.forEach((name) => {
            self.add_module_translation(translation_bundle.modules[name]);
        });
        if (translation_bundle.lang_parameters) {
            this.parameters = translation_bundle.lang_parameters;
            this.parameters.grouping = JSON.parse(this.parameters.grouping);
        }
    },
    add_module_translation: function(mod) {
        var self = this;
        mod.messages.forEach((message) => {
            self.db[message.id] = message.string;
        });
    },
    get: function(key) {
        return this.db[key];
    },
    /**
        Loads the translations from an OpenERP server.

        @param {openerp.Session} session The session object to contact the server.
        @param {Array} [modules] The list of modules to load the translation. If not specified,
        it will default to all the modules installed in the current database.
        @param {Object} [lang] lang The language. If not specified it will default to the language
        of the current user.
        @param {string} [url='/web/webclient/translations']
        @returns {Promise}
    */
    load_translations: function(session, modules, lang, url) {
        var self = this;
        var cacheId = session.cache_hashes && session.cache_hashes.translations;
        url = url || '/web/webclient/translations';
        url += '/' + (cacheId ? cacheId : Date.now());
        const paramsGet = {};
        if (modules) {
            paramsGet.mods = modules.join(',');
        }
        if (lang) {
            paramsGet.lang = lang;
        } else if (session.is_frontend && session.lang_url_code) {
            // Keep distinct cached responses per language.
            paramsGet.unique = session.lang_url_code;
        }
        return $.get(url, paramsGet).then(function (trans) {
            self.set_bundle(trans);
        });
    }
});

export default {
    database: new TranslationDataBase(),
};
