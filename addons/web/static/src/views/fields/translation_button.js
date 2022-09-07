/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { useService } from "@web/core/utils/hooks";
import { TranslationDialog } from "./translation_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const { Component, useEnv } = owl;

/**
 * Prepares a function that will open the dialog that allows to edit translation
 * values for a given field.
 *
 * It is mainly a factorization of the feature that is also used
 * in legacy_fields. We expect it to be fully implemented in TranslationButton
 * when legacy code is removed.
 */
export function useTranslationDialog() {
    const dialog = useService("dialog");
    const env = useEnv();

    async function openTranslationDialog({ record, fieldName, updateField }) {
        if (!record.resId) {
            let _continue = true;
            await new Promise((resolve) => {
                dialog.add(ConfirmationDialog, {
                    async confirm() {
                        _continue = await record.save({ stayInEdition: true });
                        resolve();
                    },
                    cancel() {
                        _continue = false;
                        resolve();
                    },
                    body: env._t(
                        "You need to save this new record before editing the translation. Do you want to proceed?"
                    ),
                    title: env._t("Warning"),
                });
            });
            if (!_continue) {
                return;
            }
        }
        const { resModel, resId } = record;

        dialog.add(TranslationDialog, {
            fieldName: fieldName,
            resId: resId,
            resModel: resModel,
            userLanguageValue: record.data[fieldName] || "",
            isComingFromTranslationAlert: false,
            updateField,
        });
    }

    return openTranslationDialog;
}

export class TranslationButton extends Component {
    setup() {
        this.user = useService("user");
        this.rpc = useService("rpc");
        this.dialog = useService("dialog");
        this.translationDialog = useTranslationDialog();
    }

    get isMultiLang() {
        return localization.multiLang;
    }
    get lang() {
        return this.user.lang.split("_")[0].toUpperCase();
    }

    onClick() {
        const { fieldName, record, updateField } = this.props;
        this.translationDialog({ fieldName, record, updateField });
    }
}
TranslationButton.template = "web.TranslationButton";
