import { Dialog } from "@web/core/dialog/dialog";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { loadLanguages, _t } from "@web/core/l10n/translation";
import { jsToPyLocale } from "@web/core/l10n/utils";

import { Component, onWillStart } from "@odoo/owl";

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

        onWillStart(async () => {
            const languages = await loadLanguages(this.orm);
            const [translations, context] = await this.loadTranslations(languages);
            let id = 1;
            translations.forEach((t) => (t.id = id++));
            this.props.isText = context.translation_type === "text";
            this.props.showSource = context.translation_show_source;

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
                    !this.props.showSource &&
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
                if (this.props.showSource) {
                    if (!translations[term.lang]) {
                        translations[term.lang] = {};
                    }
                    translations[term.lang][term.source] = updatedTermValue || term.source;
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
