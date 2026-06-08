import { localization } from "@web/core/l10n/localization";
import { useOwnedDialogs } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Record } from "@web/model/relational_model/record";
import { TranslationDialog } from "./translation_dialog";

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

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
            record.model.root instanceof Record
                ? await record.model.root.save()
                : await record.save();
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

    buttonClasses() {
        return !this.isClickable ? { "text-muted": true } : undefined;
    }
    buttonTooltip() {
        return !this.isClickable ? _t("Save this record and its parent to translate") : undefined;
    }

    get isMultiLang() {
        return localization.multiLang;
    }
    get isClickable() {
        // a new record still created inside an x2many has no id of its own to translate
        const { record } = this.props;
        return !(
            record.isNew &&
            record.model.root instanceof Record &&
            record.model.root !== record
        );
    }
    get lang() {
        return new Intl.Locale(user.lang).language.toUpperCase();
    }

    onClick() {
        if (!this.isClickable) {
            return;
        }
        const { fieldName, record } = this.props;
        this.translationDialog({ fieldName, record });
    }
}
