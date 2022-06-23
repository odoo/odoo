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
        const result = await this.rpc("/web/dataset/call_button", {
            model: "ir.translation",
            method: "translate_fields",
            args: [this.props.resModel, this.props.resId, this.props.fieldName],
            kwargs: {},
        });

        this.dialog.add(TranslationDialog, {
            domain: result.domain,
            searchName: result.context.search_default_name,
            fieldName: this.props.fieldName,
            userLanguageValue: this.props.value || "",
            isComingFromTranslationAlert: false,
            isText: result.context.translation_type === "text",
            showSource: result.context.translation_show_src,
            updateField: this.props.updateField,
        });
    }
}
TranslationButton.template = "web.TranslationButton";
