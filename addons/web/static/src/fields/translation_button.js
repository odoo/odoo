// @ts-check

/** @module @web/fields/translation_button - Translation button component and useTranslationDialog hook for translatable fields */

import { Component } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { useOwnedDialogs } from "@web/core/utils/hooks";
import { user } from "@web/services/user";

import { TranslationDialog } from "./translation_dialog";

/**
 * Prepares a function that will open the dialog that allows to edit translation
 * values for a given field.
 *
 * It is mainly a factorization of the feature that is also used
 * in legacy_fields. We expect it to be fully implemented in TranslationButton
 * when legacy code is removed.
 */
/** @returns {(params: { record: Object, fieldName: string }) => Promise<void>} Opens translation dialog */
export function useTranslationDialog() {
    const addDialog = useOwnedDialogs();

    async function openTranslationDialog({ record, fieldName }) {
        const saved = await record.save();
        if (!saved) {
            return;
        }
        const { resModel, resId } = record;

        addDialog(TranslationDialog, {
            fieldName: fieldName,
            resId: resId,
            resModel: resModel,
            userLanguageValue: record.data[fieldName] || "",
            isComingFromTranslationAlert: false,
            onSave: async () => {
                await record.load();
            },
        });
    }

    return openTranslationDialog;
}

export class TranslationButton extends Component {
    static template = "web.TranslationButton";
    static props = {
        fieldName: { type: String },
        record: { type: Object },
    };

    setup() {
        this.translationDialog = useTranslationDialog();
    }

    /** @returns {boolean} */
    get isMultiLang() {
        return localization.multiLang;
    }
    /** @returns {string} Uppercase language code (e.g. "EN") */
    get lang() {
        return new Intl.Locale(user.lang).language.toUpperCase();
    }

    onClick() {
        const { fieldName, record } = this.props;
        this.translationDialog({ fieldName, record });
    }
}
