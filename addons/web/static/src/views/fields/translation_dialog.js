/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { loadLanguages, _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { Component, onWillStart, useState } from "@odoo/owl";

export class TranslationDialog extends Component {
    setup() {
        super.setup();
        this.title = sprintf(this.env._t("Translate: %s"), this.props.fieldName);

        this.orm = useService("orm");
        this.user = useService("user");

        this.state = useState({ terms: [] });

        onWillStart(async () => {
            const [translations, context] = await this.loadTranslations();
            let id = 1;
            translations.forEach((t) => (t.id = id++));
            this.props.languages = await loadLanguages(this.orm);
            this.props.isText = ["text", "html"].includes(context.field_type);
            this.props.translateType = context.translate_type;
            this.props.enUSActivated = context.en_US_activated;
            if (!this.props.enUSActivated) {
                this.props.languages.push(["en_US", _t("Source Value")]);
            }

            this.state.terms.push(
                ...translations.map((term) => {
                    const relatedLanguage = this.props.languages.find((l) => l[0] === term.lang);
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
                })
            );
            this.state.terms.sort((a, b) => a.langName.localeCompare(b.langName));
        });
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

        const resetLangs = [];
        this.props.languages.forEach(([language, languageName]) => {
            if (
                !this.state.terms.some(
                    (t) => t.lang === language && (t.translated || !t.isModified)
                )
            ) {
                resetLangs.push(language);
            }
        });

        this.state.terms.map((term) => {
            if (term.isModified && !resetLangs.includes(term.lang)) {
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
            resetLangs,
        ]);

        await this.props.onSave();
        this.props.close();
    }

    onUpdate(term, ev) {
        const newValue = ev.target.value;
        if (!this.checkValue(term, newValue)) {
            ev.target.value = term.value;
            return;
        }
        if (newValue) {
            term.isModified = true;
            term.translated = true;
            term.value = newValue;
            if (term.lang === "en_US") {
                // update source and other fallback value
                this.state.terms.forEach((t) => {
                    if (t.source === term.source) {
                        t.source = newValue;
                        if (!t.translated) {
                            t.value = newValue;
                        }
                    }
                });
            }
        } else {
            term.isModified = term.isModified || term.translated;
            term.translated = false;
            ev.target.value = term.value = term.source;
        }
    }

    checkValue(term, value) {
        if (
            value &&
            term.lang === "en_US" &&
            this.state.terms.some(
                (t) => t.value === value && t.id != term.id && t.lang === term.lang
            )
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
