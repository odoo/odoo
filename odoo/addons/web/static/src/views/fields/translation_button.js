/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { TranslationDialog } from "./translation_dialog";

import { Component } from "@odoo/owl";

/**
 * Prepares a function that will open the dialog that allows to edit translation
 * values for a given field.
 *
 * It is mainly a factorization of the feature that is also used
 * in legacy_fields. We expect it to be fully implemented in TranslationButton
 * when legacy code is removed.
 */
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
    setup() {
        this.user = useService("user");
        this.translationDialog = useTranslationDialog();
    }

    get isMultiLang() {
        return localization.multiLang;
    }
    get lang() {
        return this.user.lang.split("_")[0].toUpperCase();
    }

    onClick() {
        const { fieldName, record } = this.props;
        this.translationDialog({ fieldName, record });
    }
}
TranslationButton.template = "web.TranslationButton";
TranslationButton.props = {
    fieldName: { type: String },
    record: { type: Object },
};
