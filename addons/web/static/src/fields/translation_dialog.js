// @ts-check

/** @module @web/fields/translation_dialog - Dialog for editing field translation values across installed languages */

import { Component, onWillStart } from "@odoo/owl";
import { _t, loadLanguages } from "@web/core/l10n/translation";
import { jsToPyLocale } from "@web/core/l10n/utils";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/services/user";
import { Dialog } from "@web/ui/dialog/dialog";

export class TranslationDialog extends Component {
    static template = "web.TranslationDialog";
    static components = { Dialog };
    static props = {
        fieldName: String,
        resId: Number,
        resModel: String,
        userLanguageValue: { type: String, optional: true },
        isComingFromTranslationAlert: { type: Boolean, optional: true },
        onSave: Function,
        close: Function,
        isText: { type: Boolean, optional: true },
        showSource: { type: Boolean, optional: true },
    };
    setup() {
        super.setup();
        this.title = _t("Translate: %s", this.props.fieldName);

        this.user = user;
        this.orm = useService("orm");

        this.terms = [];
        this.updatedTerms = {};
        this.isText = this.props.isText ?? false;
        this.showSource = this.props.showSource ?? false;

        onWillStart(async () => {
            const languages = await loadLanguages(this.orm);
            const [translations, context] = await this.loadTranslations(languages);
            let id = 1;
            translations.forEach((t) => (t.id = id++));
            this.isText = context.translation_type === "text";
            this.showSource = context.translation_show_source;

            this.terms = translations.map((term) => {
                const relatedLanguage = languages.find((l) => l[0] === term.lang);
                const termInfo = {
                    ...term,
                    langName: relatedLanguage[1],
                    value: term.value || "",
                };
                // we set the translation value coming from the database, except for the language
                // the user is currently utilizing. Then we set the translation value coming
                // from the value of the field in the form
                if (
                    term.lang === jsToPyLocale(user.lang) &&
                    !this.showSource &&
                    !this.props.isComingFromTranslationAlert
                ) {
                    this.updatedTerms[term.id] = this.props.userLanguageValue;
                    termInfo.value = this.props.userLanguageValue;
                }
                return termInfo;
            });
            this.terms.sort((a, b) => a.langName.localeCompare(b.langName));
        });
    }

    /** @returns {Array} Domain filter for translation search */
    get domain() {
        const domain = this.props.domain;
        if (this.props.searchName) {
            domain.push(["name", "=", `${this.props.searchName}`]);
        }
        return domain;
    }

    /**
     * Load the translation terms for the installed language, for the current model and res_id
     */
    async loadTranslations(languages) {
        return this.orm.call(this.props.resModel, "get_field_translations", [
            [this.props.resId],
            this.props.fieldName,
        ]);
    }

    /**
     * Save all the terms that have been updated
     */
    async onSave() {
        const translations = {};

        this.terms.map((term) => {
            const updatedTermValue = this.updatedTerms[term.id];
            if (term.id in this.updatedTerms && term.value !== updatedTermValue) {
                if (this.showSource) {
                    if (!translations[term.lang]) {
                        translations[term.lang] = {};
                    }
                    translations[term.lang][term.source] =
                        updatedTermValue || term.source;
                } else {
                    translations[term.lang] = updatedTermValue || false;
                }
            }
        });

        await this.orm.call(this.props.resModel, "update_field_translations", [
            [this.props.resId],
            this.props.fieldName,
            translations,
        ]);

        await this.props.onSave();
        this.props.close();
    }
}
