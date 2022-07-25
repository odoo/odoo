/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { useService } from "@web/core/utils/hooks";
import { TranslationDialog } from "./translation_dialog";

const { Component } = owl;

export class TranslationButton extends Component {
    setup() {
        this.user = useService("user");
        this.rpc = useService("rpc");
        this.dialog = useService("dialog");
    }

    get isMultiLang() {
        return localization.multiLang;
    }
    get lang() {
        return this.user.lang.split("_")[0].toUpperCase();
    }

    async onClick() {

        this.dialog.add(TranslationDialog, {
            fieldName: this.props.fieldName,
            resId: this.props.resId,
            userLanguageValue: this.props.value || "",
            resModel: this.props.resModel,
            isComingFromTranslationAlert: false,
            updateField: this.props.updateField,
        });
    }
}
TranslationButton.template = "web.TranslationButton";
