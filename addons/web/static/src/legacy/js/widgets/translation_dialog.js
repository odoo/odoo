odoo.define('web.TranslationDialog', function (require) {
    'use strict';

    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var session = require('web.session');

    var _t = core._t;

    var TranslationDialog = Dialog.extend({
        template: 'web.TranslationDialogWidget',

        /**
         * @constructor
         * @param {Widget} parent
         * @param {Object} [options]
         * @param {string} [options.fieldName] the name of the field currently translated (from the model of the form view)
         * @param {integer} [options.resId] the ID of record currently translated
         * @param {string} [options.userLanguageValue] the value of the translation in the language of the user, as seen in the from view (might be empty)
         * @param {string} [options.dataPointID] the data point id of the record for which we do the translations
         * @param {boolean} [options.isComingFromTranslationAlert] the initiator of the dialog, might be a link on a field or the translation alert on top of the form
         *
         */
        init: function (parent, options) {
            options = options || {};

            this.fieldName = options.fieldName;
            this.resId = options.resId;
            this.userLanguageValue = options.userLanguageValue;
            this.dataPointModel = options.dataPointModel;
            this.dataPointID = options.dataPointID;
            this.isComingFromTranslationAlert = options.isComingFromTranslationAlert;
            this.currentInterfaceLanguage = session.user_context.lang;
            this.context = options.context;

            this._super(parent, _.extend({
                size: 'large',
                title: _.str.sprintf(_t('Translate: %s'), this.fieldName),
                buttons: [
                    { text: _t('Save'), classes: 'btn-primary', close: true, click: this._onSave.bind(this) },
                    { text: _t('Discard'), close: true },
                ],
            }, options));
        },
        /**
         * @override
         */
        willStart: function () {
            return Promise.all([
                this._super(),
                this._loadLanguages().then((l) => {
                    this.languages = l;
                    return this._loadTranslations().then((t) => {
                        [this.translations, this.context] = t;
                        let id = 1;
                        this.translations.forEach((t) => t['id'] = id++);
                        this.isText = this.context.translation_type === 'text';
                        this.showSource = this.context.translation_show_source;
                    });
                }),
            ]).then(() => {
                this.data = this.translations.map((term) => {
                    let relatedLanguage = this.languages.find((language) => language[0] === term.lang);
                    return {
                        id: term.id,
                        lang: term.lang,
                        langName: relatedLanguage[1],
                        source: term.source,
                        // we set the translation value coming from the database, except for the language
                        // the user is currently utilizing. Then we set the translation value coming
                        // from the value of the field in the form
                        value: (term.lang === this.currentInterfaceLanguage &&
                            !this.showSource &&
                            !this.isComingFromTranslationAlert) ?
                            this.userLanguageValue : term.value || ''
                    };
                });
                this.data.sort((left, right) =>
                    left.langName.localeCompare(right.langName));
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Load the translation terms for the installed language, for the current model and res_id
         * @private
         */
        _loadTranslations: function () {
            return this._rpc({
                model: this.dataPointModel,
                method: 'get_field_translations',
                args: [[this.resId], this.fieldName],
                context: this.context,
            });
        },
        /**
         * Load the installed languages long names and code
         *
         * The result of the call is put in cache on the prototype of this dialog.
         * If any new language is installed, a full page refresh will happen,
         * so there is no need invalidate it.
         * @private
         */
        _loadLanguages: function () {
            if (TranslationDialog.prototype.installedLanguagesCache)
                return Promise.resolve(TranslationDialog.prototype.installedLanguagesCache);

            return this._rpc({
                model: 'res.lang',
                method: 'get_installed',
                fields: ['code', 'name', 'iso_code'],
            }).then((installedLanguages) => {
                TranslationDialog.prototype.installedLanguagesCache = installedLanguages;
                return TranslationDialog.prototype.installedLanguagesCache
            });
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        /**
         * Save all the terms that have been updated
         * @private
         * @returns a promise that is resolved when all the save have occured
         */
        _onSave: function () {
            var updatedTerm = {};
            var updateFormViewField;

            this.el.querySelectorAll('input[type=text],textarea').forEach((t) => {
                var initialValue = this.data.find((d) => d.id == t.dataset.id);
                if (initialValue.value !== t.value) {
                    updatedTerm[t.dataset.id] = {lang: initialValue.lang, source: initialValue.source, value: t.value};

                    if (initialValue.lang === this.currentInterfaceLanguage && !this.showSource) {
                        // when the user has changed the term for the language he is
                        // using in the interface, this change should be reflected
                        // in the form view
                        // partial translations being handled server side are
                        // also ignored
                        var changes = {};
                        changes[this.fieldName] = t.value;
                        updateFormViewField = {
                            dataPointID: this.dataPointID,
                            changes: changes,
                            doNotSetDirty: false,
                        };
                    }
                }
            });

            // updatedTerm only contains the id and values of the terms that
            // have been updated by the user
            const translations = {};
            if (this.showSource) { // model terms translation
                Object.entries(updatedTerm).forEach(([id, term]) => {
                    if (!translations[term.lang]) {
                       translations[term.lang] = {};
                    }
                    translations[term.lang][term.source] = term.value;
                });
            }
            else { // model translation
                Object.entries(updatedTerm).forEach(([id, term]) => translations[term.lang] = term.value);
            }
            return this._rpc({
                model: this.dataPointModel,
                method: 'update_field_translations',
                args: [[this.resId], this.fieldName, translations],
            }).then(() => {
                // we might have to update the value of the field on the form
                // view that opened the translation dialog
                if (updateFormViewField) {
                    this.trigger_up('field_changed', updateFormViewField);
                }
            });
        }
    });

    return TranslationDialog;
});
