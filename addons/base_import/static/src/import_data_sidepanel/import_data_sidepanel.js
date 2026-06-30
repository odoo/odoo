import { Component } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { _t } from "@web/core/l10n/translation";
import { DocumentationLink } from "@web/views/widgets/documentation_link/documentation_link";

export class ImportDataSidepanel extends Component {
    static template = "ImportDataSidepanel";
    static components = { CheckBox, DocumentationLink };
    static props = {
        filename: { type: String },
        formattingOptions: { type: Object, optional: true },
        options: { type: Object },
        importTemplates: { type: Array, optional: true },
        isBatched: { type: Boolean, optional: true },
        onOptionChanged: { type: Function },
        onReload: { type: Function },
        hasBinaryFields: { type: Boolean },
        binaryFilesParams: { type: Object },
        onBinaryFilesParamsChanged: { type: Function },
    };

    get fileName() {
        return this.props.filename.split(".")[0];
    }

    get fileExtension() {
        return "." + this.props.filename.split(".").pop();
    }

    getOptionValue(name) {
        if (name === "skip") {
            return (this.props.options.skip + 1).toString();
        }
        return this.props.options[name].toString();
    }

    setOptionValue(name, value) {
        this.props.onOptionChanged(name, isNaN(parseFloat(value)) ? value : Number(value));
    }

    // Start at row 1 = skip 0 lines
    onLimitChange(ev) {
        this.props.onOptionChanged("skip", ev.target.value ? ev.target.value - 1 : 0);
    }

    get binaryFilesLabel() {
        const files = this.props.binaryFilesParams.binaryFiles.value;
        const number = Object.keys(files).length;
        if (number > 0) {
            return _t("%(number)s file(s) selected", { number });
        }
        return _t("No file selected");
    }
}
