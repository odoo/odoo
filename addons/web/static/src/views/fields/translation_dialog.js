/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { loadLanguages } from "@web/core/l10n/translation";

const { Component, onWillStart } = owl;

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
            const translations = await this.loadTranslations(languages);

            this.terms = translations.map((term) => {
                const relatedLanguage = languages.find((l) => l[0] === term.lang);
                if (!term.value && !this.props.showSource) {
                    term.value = term.src;
                }
                return {
                    id: term.id,
                    lang: term.lang,
                    langName: relatedLanguage[1],
                    source: term.src,
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
            this.terms.sort((a, b) =>
                a.langName < b.langName || (a.langName === b.langName && a.source < b.source)
                    ? -1
                    : 1
            );
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
        const domain = [...this.domain, ["lang", "in", languages.map((l) => l[0])]];
        return this.orm.searchRead("ir.translation", domain, ["lang", "src", "value"]);
    }

    /**
     * Save all the terms that have been updated
     */
    async onSave() {
        await Promise.all(
            this.terms.map(async (term) => {
                if (term.id in this.updatedTerms && term.value !== this.updatedTerms[term.id]) {
                    await this.orm.write("ir.translation", [term.id], {
                        value: this.updatedTerms[term.id],
                    });
                }
            })
        );

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
