import { localization } from "@web/core/l10n/localization";
import { useOwnedDialogs } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Record } from "@web/model/relational_model/record";
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
        // in case of DynamicList list views model.root won't be a Record but a DynamicList itself
        const saved =
            record.model.root instanceof Record ? await record.model.root.save() : await record.save();
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

    get isMultiLang() {
        return localization.multiLang;
    }
    get lang() {
        return new Intl.Locale(user.lang).language.toUpperCase();
    }

    onClick() {
        const { fieldName, record } = this.props;
        this.translationDialog({ fieldName, record });
    }
}
