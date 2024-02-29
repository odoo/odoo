
odoo.define('web.translation', function (require) {
"use strict";

var Class = require('web.Class');
const { _lt } = require("@web/core/l10n/translation");

var TranslationDataBase = Class.extend(/** @lends instance.TranslationDataBase# */{
    init: function() {
        this.db = {};
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
        var modules = _.keys(translation_bundle.modules);
        modules.sort();
        if (_.include(modules, "web")) {
            modules = ["web"].concat(_.without(modules, "web"));
        }
        _.each(modules, function(name) {
            self.add_module_translation(translation_bundle.modules[name]);
        });
        if (translation_bundle.lang_parameters) {
            this.parameters = translation_bundle.lang_parameters;
            this.parameters.grouping = JSON.parse(this.parameters.grouping);
        }
    },
    add_module_translation: function(mod) {
        var self = this;
        _.each(mod.messages, function(message) {
            self.db[message.id] = message.string;
        });
    },
    build_translation_function: function() {
        var self = this;
        var fcnt = function(str) {
            var tmp = self.get(str);
            return tmp === undefined ? str : tmp;
        };
        fcnt.database = this;
        return fcnt;
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
        url = url || new URL("/web/webclient/translations", session.origin || location.origin).href;
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

/**
 * Eager translation function, performs translation immediately at call
 * site. Beware using this outside of method bodies (before the
 * translation database is loaded), you probably want :func:`_lt`
 * instead.
 *
 * @function _t
 * @param {String} source string to translate
 * @returns {String} source translated into the current locale
 */
var _t = new TranslationDataBase().build_translation_function();

/** Setup jQuery timeago */
/*
 * Strings in timeago are "composed" with prefixes, words and suffixes. This
 * makes their detection by our translating system impossible. Use all literal
 * strings we're using with a translation mark here so the extractor can do its
 * job.
 */
{
    _t('less than a minute ago');
    _t('about a minute ago');
    _t('%d minutes ago');
    _t('about an hour ago');
    _t('%d hours ago');
    _t('a day ago');
    _t('%d days ago');
    _t('about a month ago');
    _t('%d months ago');
    _t('about a year ago');
    _t('%d years ago');
}


return {
    _t: _t,
    _lt: _lt,
    TranslationDataBase: TranslationDataBase,
};

});
