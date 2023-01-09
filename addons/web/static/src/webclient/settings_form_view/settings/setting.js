/** @odoo-module **/

import { escapeRegExp } from "@web/core/utils/strings";
import { HighlightText } from "../highlight_text/highlight_text";
import { session } from "@web/session";
import { FormLabelHighlightText } from "../highlight_text/form_label_highlight_text";
import { Component, useState } from "@odoo/owl";

export class Setting extends Component {
    setup() {
        this.state = useState({
            search: this.env.searchState,
            showAllContainer: this.env.showAllContainer,
        });
        this.labels = this.props.labels || [];
        this.labels.push(this.labelString, this.props.help);
        if (this.props.fieldName) {
            this.fieldType = this.props.record.fields[this.props.fieldName].type;
            if (
                typeof this.props.fieldInfo.modifiers.readonly === "boolean" &&
                this.props.fieldInfo.modifiers.readonly === true
            ) {
                this.notMuttedLabel = true;
            }
        }
    }

    get classNames() {
        const { class: _class } = this.props;
        const classNames = {
            o_setting_box: true,
            "col-12": true,
            "col-lg-6": true,
            o_searchable_setting: Boolean(this.labels.length),
            [_class]: Boolean(_class),
        };

        return classNames;
    }

    get displayCompanyDependentIcon() {
        return (
            this.labelString && this.props.companyDependent && session.display_switch_company_menu
        );
    }

    get labelString() {
        if (this.props.string) {
            return this.props.string;
        }
        const label =
            this.props.record &&
            this.props.record.fields[this.props.fieldName] &&
            this.props.record.fields[this.props.fieldName].string;
        return label || "";
    }

    get url() {
        if (this.props.documentation.startsWith("^https?://")) {
            return this.props.documentation;
        } else {
            const serverVersion = session.server_version.includes("alpha")
                ? "master"
                : session.server_version;
            return "https://www.odoo.com/documentation/" + serverVersion + this.props.documentation;
        }
    }
    visible() {
        if (!this.state.search.value) {
            return true;
        }
        if (this.state.showAllContainer.showAllContainer) {
            return true;
        }
        const regexp = new RegExp(escapeRegExp(this.state.search.value), "i");
        if (regexp.test(this.labels.join())) {
            return true;
        }
        return false;
    }
}
Setting.components = {
    FormLabelHighlightText,
    HighlightText,
};
Setting.template = "web.Setting";
Setting.props = {
    labels: { type: Array, optional: 1 },
    title: { type: String, optional: 1 },
    fieldId: { type: String, optional: 1 },
    help: { type: String, optional: 1 },
    fieldName: { type: String, optional: 1 },
    fieldInfo: { type: Object, optional: 1 },
    class: { type: String, optional: 1 },
    record: { type: Object, optional: 1 },
    documentation: { type: String, optional: 1 },
    string: { type: String, optional: 1 },
    addLabel: { type: Boolean },
    companyDependent: { type: Boolean, optional: 1 },
    slots: { type: Object, optional: 1 },
};
