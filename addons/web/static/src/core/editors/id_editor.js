/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { RecordAutocomplete } from "@web/core/record_selectors/record_autocomplete";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Expression, doFormatValue } from "@web/core/tree_editor/condition_tree";
import { _protectMethod } from "@web/core/utils/hooks";

export const isId = (val) => Number.isInteger(val) && val >= 1;

async function getDisplayName(value, resModel, component) {
    if (!value) {
        return "";
    }
    if (isId(value)) {
        const { [value]: displayName } = await _protectMethod(component, () =>
            component.env.services.name.loadDisplayNames(resModel, [value])
        )();
        return typeof displayName === "string"
            ? displayName
            : _t("Inaccessible/missing record ID: %s", value);
    }
    return value instanceof Expression
        ? String(value)
        : _t("Invalid record ID: %s", doFormatValue(value));
}

export class IdSelector extends Component {
    static template = "web.IdEditor";
    static components = { RecordAutocomplete };
    static props = {
        value: {},
        resModel: String,
        update: Function,
        multiSelect: { type: Boolean, optional: true },
        currentValues: { type: Array, optional: true },
        domain: { type: Array, optional: true },
        context: { type: Object, optional: true },
        fieldString: { type: String, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        multiSelect: false,
        currentValues: [],
    };

    setup() {
        onWillStart(() => this.computeDerivedParams(this.props));
        onWillUpdateProps((nextProps) => this.computeDerivedParams(nextProps));
    }

    async computeDerivedParams(props) {
        const { resModel, value } = props;
        this.displayName = await getDisplayName(value, resModel, this);
    }

    update(resIds) {
        this.props.update(...resIds);
        this.render(true);
    }

    getIds() {
        if (this.props.multiSelect) {
            return [...this.props.currentValues, this.props.value].filter((val) => isId(val));
        }
        return [];
    }
}

registry.category("editors").add("id", (genericProps) => {
    const { resModel } = genericProps;
    return {
        component: IdSelector,
        isSupported: () => true,
        defaultValue: () => false,
        serialize: (value, component) => {
            return getDisplayName(value, resModel, component);
        },
    };
});
