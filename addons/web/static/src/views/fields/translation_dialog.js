/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { loadLanguages } from "@web/core/l10n/translation";

import { Component, onWillStart } from "@odoo/owl";

export class TranslationDialog extends Component {
    setup() {
        super.setup();
        this.title = sprintf(this.env._t("Translate: %s"), this.props.fieldName);

        this.orm = useService("orm");
        this.user = useService("user");

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
                return {
                    id: term.id,
                    lang: term.lang,
                    langName: relatedLanguage[1],
                    source: term.source,
                    // we set the translation value coming from the database, except for the language
                    // the user is currently utilizing. Then we set the translation value coming
                    // from the value of the field in the form
                    value:
                        term.lang === this.user.lang &&
                        !this.props.showSource &&
                        !this.props.isComingFromTranslationAlert
                            ? this.props.userLanguageValue
                            : term.value || "",
                };
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
                    const source = term.value ? term.value : term.source;
                    translations[term.lang][source] = updatedTermValue;
                } else {
                    translations[term.lang] = updatedTermValue;
                }
            }
        });

        await this.orm.call(this.props.resModel, "update_field_translations", [
            [this.props.resId],
            this.props.fieldName,
            translations,
        ]);

        // we might have to update the value of the field on the form
        // view that opened the translation dialog
        const currentTerm = this.terms.find(
            (term) => term.lang === this.user.lang && !this.props.showSource
        );
        if (
            currentTerm &&
            currentTerm.id in this.updatedTerms &&
            currentTerm.value !== this.updatedTerms[currentTerm.id]
        ) {
            this.props.updateField(this.updatedTerms[currentTerm.id]);
        }

        this.props.close();
    }
}
TranslationDialog.template = "web.TranslationDialog";
TranslationDialog.components = { Dialog };
