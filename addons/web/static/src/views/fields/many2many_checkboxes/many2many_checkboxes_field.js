import { Component, onWillUnmount } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "../standard_field_props";
import { ConnectionLostError } from "@web/core/network/rpc";
import { x2ManyCommands } from "@web/core/orm_service";

export class Many2ManyCheckboxesField extends Component {
    static template = "web.Many2ManyCheckboxesField";
    static components = { CheckBox };
    static props = {
        ...standardFieldProps,
        domain: { type: [Array, Function], optional: true },
        context: { type: Object, optional: true },
    };

    setup() {
        this.specialData = useSpecialData((orm, props) => {
            const { relation } = props.record.fields[props.name];
            const domain = getFieldDomain(props.record, props.name, props.domain);
            return orm
                .call(relation, "name_search", ["", domain], {
                    context: this.props.context || {},
                })
                .catch((error) => {
                    if (error instanceof ConnectionLostError) {
                        return this.props.record.data[this.props.name].records.map((r) => [
                            r.resId,
                            r.data.display_name,
                        ]);
                    }
                    throw error;
                });
        });
        // these two sets track pending changes in the relation, and allow us to
        // batch consecutive changes into a single replaceWith, thus saving
        // unnecessary potential intermediate onchanges
        this.idsToAdd = {};
        this.idsToRemove = {};
        this.debouncedCommitChanges = debounce(this.commitChanges.bind(this), 500);
        useBus(this.props.record.model.bus, "NEED_LOCAL_CHANGES", this.commitChanges.bind(this));
        onWillUnmount(this.commitChanges.bind(this));
    }

    get items() {
        return this.specialData.data;
    }

    isSelected(item) {
        return this.props.record.data[this.props.name].currentIds.includes(item[0]);
    }

    commitChanges() {
        if (Object.keys(this.idsToAdd).length === 0 && Object.keys(this.idsToRemove).length === 0) {
            return;
        }
        const commands = [
            ...Object.values(this.idsToAdd).map((add) => [
                x2ManyCommands.LINK,
                add.id,
                { id: add.id, display_name: add.displayName },
            ]),
            ...Object.values(this.idsToRemove).map((rem) => [x2ManyCommands.UNLINK, rem.id]),
        ];

        this.idsToAdd = {};
        this.idsToRemove = {};
        return this.props.record.data[this.props.name].applyCommands(commands);
    }

    onChange(resId, displayName, checked) {
        if (checked) {
            if (resId in this.idsToRemove) {
                delete this.idsToRemove[resId];
            } else {
                this.idsToAdd[resId] = { id: resId, displayName };
            }
        } else {
            if (resId in this.idsToAdd) {
                delete this.idsToAdd[resId];
            } else {
                this.idsToRemove[resId] = { id: resId, displayName };
            }
        }
        this.debouncedCommitChanges();
    }
}

export const many2ManyCheckboxesField = {
    component: Many2ManyCheckboxesField,
    displayName: _t("Checkboxes"),
    supportedTypes: ["many2many"],
    relatedFields: () => [{ name: "display_name", type: "char" }],
    isEmpty: () => false,
    extractProps(fieldInfo, dynamicInfo) {
        return {
            domain: dynamicInfo.domain,
            context: dynamicInfo.context,
        };
    },
};

registry.category("fields").add("many2many_checkboxes", many2ManyCheckboxesField);
