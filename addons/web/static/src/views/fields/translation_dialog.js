/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { loadLanguages, _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { Component, onWillStart } from "@odoo/owl";

export class TranslationDialog extends Component {
    setup() {
        super.setup();
        this.title = sprintf(this.env._t("Translate: %s"), this.props.fieldName);

        this.orm = useService("orm");
        this.user = useService("user");

        this.terms = [];

        onWillStart(async () => {
            const languages = await loadLanguages(this.orm);
            const [translations, context] = await this.loadTranslations();
            let id = 1;
            translations.forEach((t) => (t.id = id++));
            this.props.isText = ["text", "html"].includes(context.field_type);
            this.props.translateType = context.translate_type;
            this.props.enUSActivated = context.en_US_activated;
            if (!this.props.enUSActivated) {
                languages.push(["en_US", _t("Source Value")]);
            }

            this.terms = translations.map((term) => {
                const relatedLanguage = languages.find((l) => l[0] === term.lang);
                const termInfo = {
                    ...term,
                    langName: relatedLanguage[1],
                    oldValue: term.value,
                    isModified: false,
                };
                // we set the translation value coming from the database, except for the language
                // the user is currently utilizing. Then we set the translation value coming
                // from the value of the field in the form
                if (
                    term.lang === this.user.lang &&
                    this.props.translateType === "model" &&
                    !this.props.isComingFromTranslationAlert
                ) {
                    termInfo.value = this.props.userLanguageValue;
                    termInfo.isModified = true;
                    termInfo.translated = true;
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
    async loadTranslations() {
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
            if (term.isModified) {
                if (this.props.translateType === "model_terms") {
                    if (!translations[term.lang]) {
                        translations[term.lang] = {};
                    }
                    translations[term.lang][term.oldValue] = term.value;
                } else {
                    // this.props.translateType === "model"
                    translations[term.lang] = term.value;
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

    onUpdate(term, ev) {
        if (!this.check_value(term, ev.target.value)) {
            ev.target.value = term.value;
            return;
        }
        if (!term.translated && !ev.target.value) {
            ev.target.value = term.value;
            return;
        }
        term.translated = !!ev.target.value;
        term.isModified = true;
        if (term.translated) {
            if (term.lang === "en_US") {
                const oldSource = term.source;
                const newSource = ev.target.value;
                // update source and other fallback value
                const valueToUpdate = [];
                this.terms.forEach((t) => {
                    if (t.source === oldSource) {
                        t.source = newSource;
                        if (!t.translated) {
                            t.value = newSource;
                            valueToUpdate.push(t.id.toString());
                        }
                    }
                });
                // update UI
                for (const t of document.getElementsByClassName("o_field_translate_fallback")) {
                    if (valueToUpdate.includes(t.dataset.id)) {
                        t.value = newSource;
                    }
                }
            }
            ev.target.classList.remove("o_field_translate_fallback");
            term.value = ev.target.value;
        } else {
            ev.target.classList.add("o_field_translate_fallback");
            if (this.props.translateType === "model_terms") {
                term.value = term.source;
            } else {
                term.value = false;
            }
            ev.target.value = term.source;
        }
    }

    check_value(term, value) {
        if (
            value &&
            term.lang === "en_US" &&
            this.terms.some((t) => t.value === value && t.id != term.id && t.lang === term.lang)
        ) {
            this.props.addDialog(AlertDialog, {
                body: _t("Two sources cannot be the same"),
            });
            return false;
        }
        if (!value && term.lang === "en_US") {
            this.props.addDialog(AlertDialog, {
                body: sprintf(
                    _t("%s cannot be assigned to empty in the translation dialog"),
                    term.langName
                ),
            });
            return false;
        }
        return true;
    }
}
TranslationDialog.template = "web.TranslationDialog";
TranslationDialog.components = { Dialog };
