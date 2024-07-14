/** @odoo-module */
import { Field } from "@web/views/fields/field";
import { FieldContentOverlay } from "./field_content_overlay";

import { useStudioRef, studioIsVisible } from "@web_studio/client_action/view_editor/editors/utils";

import { useState } from "@odoo/owl";

/*
 * Field:
 * - Displays an Overlay for X2Many fields
 * - handles invisible
 */
export class FieldStudio extends Field {
    setup() {
        super.setup();
        this.state = useState({
            displayOverlay: false,
        });
        useStudioRef("rootRef", this.onClick);
    }
    get fieldComponentProps() {
        const fieldComponentProps = super.fieldComponentProps;
        delete fieldComponentProps.studioXpath;
        delete fieldComponentProps.hasEmptyPlaceholder;
        delete fieldComponentProps.hasLabel;
        delete fieldComponentProps.studioIsVisible;
        return fieldComponentProps;
    }
    get classNames() {
        const classNames = super.classNames;
        classNames["o_web_studio_show_invisible"] = !studioIsVisible(this.props);
        classNames["o-web-studio-editor--element-clickable"] = !!this.props.studioXpath;
        if (this.studioIsEmpty()) {
            delete classNames["o_field_empty"];
            classNames["o_web_studio_widget_empty"] = true;
        }
        return classNames;
    }

    studioIsEmpty() {
        const { name, record, hasLabel } = this.props;
        if (hasLabel) {
            return false;
        }
        return "isEmpty" in this.field ? this.field.isEmpty(record, name) : !record.data[name];
    }

    getEmptyPlaceholder() {
        const { hasEmptyPlaceholder, name, record, fieldInfo } = this.props;
        if (!hasEmptyPlaceholder) {
            return false;
        }
        return this.studioIsEmpty() && (fieldInfo.string || record.fields[name].string);
    }

    isX2ManyEditable(props) {
        const { name, record } = props;
        const field = record.fields[name];
        if (!["one2many", "many2many"].includes(field.type)) {
            return false;
        }
        return !!this.props.fieldInfo.field.useSubView;
    }

    onEditViewType(viewType) {
        const { name, record, studioXpath } = this.props;
        this.env.viewEditorModel.editX2ManyView({
            viewType,
            fieldName: name,
            record,
            xpath: studioXpath,
            fieldContext: this.fieldComponentProps.context,
        });
    }

    onClick(ev) {
        if (ev.target.classList.contains("o_web_studio_editX2Many")) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        this.env.config.onNodeClicked(this.props.studioXpath);
        this.state.displayOverlay = !this.state.displayOverlay;
    }
}
FieldStudio.components = { ...Field.components, FieldContentOverlay };
FieldStudio.template = "web_studio.Field";
