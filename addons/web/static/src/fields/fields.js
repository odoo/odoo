/** @odoo-module **/
import { registry } from "@web/core/registry";
import legacyFieldRegistry from "web.field_registry";
import owlFieldRegistry from "web.field_registry_owl";
import { ComponentAdapter } from "web.OwlCompatibility";
import { useEffect } from "@web/core/utils/hooks";

const { Component, tags, hooks } = owl;

const fieldRegistry = registry.category("fields");

function getFieldFromRegistry(registry, { fieldType, viewType, fieldName, fieldsDescription }) {
    if (viewType && fieldType) {
        const specificType = `${viewType}.${fieldType}`;
        if (registry.contains(specificType)) {
            return registry.get(specificType);
        }
    }
    if (!registry.contains(fieldType)) {
        const field = fieldsDescription[fieldName];
        fieldType = field && field.type;
    }
    return registry.get(fieldType, null);
}

class Field extends Component {
    static getTangibleField({ record, type, name }) {
        const FieldClass = getFieldFromRegistry(fieldRegistry, {
            fieldName: name,
            fieldType: type,
            viewType: record.viewtype,
            fieldsDescription: record.fields,
        });
        return { FieldClass };
    }

    setup() {
        const { record, type, name } = this.props;
        this.fieldRef = hooks.useRef("fieldRef");
        this.FieldComponent = Field.getTangibleField({ record, type, name }).FieldClass;
    }
}

Field.template = tags.xml/* xml */ `
    <t t-component="FieldComponent" t-props="props" class="o-field" t-key="props.record.id" t-ref="fieldRef"/>
`;

class FieldSupportsLegacy extends Field {
    static getTangibleField({ record, type, fieldName }) {
        let { FieldClass } = super.getTangibleField(...arguments);
        if (!FieldClass) {
            FieldClass = getFieldFromRegistry(owlFieldRegistry, {
                fieldName,
                fieldType: type,
                viewType: record.viewType,
                fieldsDescription: record.fields,
            });
            if (FieldClass) {
                return { FieldClass, isOwlLegacy: true };
            } else {
                FieldClass = getFieldFromRegistry(legacyFieldRegistry, {
                    fieldName,
                    fieldType: type,
                    viewType: record.viewType,
                    fieldsDescription: record.fields,
                });
                return { FieldClass, isLegacy: true };
            }
        }
        return {};
    }

    setup() {
        super.setup();
        this.renderId = 0;
        useEffect(() => {
            this.renderId++;
        });
        if (!this.FieldComponent) {
            this.env = owl.Component.env;
            const { record, type, name } = this.props;
            const { FieldClass, isOwlLegacy, isLegacy } = FieldSupportsLegacy.getTangibleField({
                record,
                type,
                name,
            });
            this.FieldComponent = FieldClass;
            this.isOwlLegacy = isOwlLegacy;
            this.isLegacy = isLegacy;
        }
    }

    get legacyProps() {
        const legacyRecord = Object.assign({}, this.props.model._legacyRecord_);
        legacyRecord.data = Object.assign({}, legacyRecord.data, this.props.record.data);
        return {
            fieldName: this.props.name,
            record: legacyRecord,
        };
    }

    get widgetArgs() {
        const { fieldName, record } = this.legacyProps;
        return [fieldName, record];
    }
}
FieldSupportsLegacy.template = tags.xml/* xml */ `<t>
    <t t-if="!isOwlLegacy and !isLegacy" t-call="${Field.template}" />
    <t t-elif="isOwlLegacy" t-component="FieldComponent" t-props="legacyProps" />
    <t t-elif="isLegacy" t-component="ComponentAdapter" widgetArgs="widgetArgs" Component="FieldComponent" t-key="renderId" />
</t>
`;
FieldSupportsLegacy.components = { ComponentAdapter };

export { FieldSupportsLegacy as Field };
