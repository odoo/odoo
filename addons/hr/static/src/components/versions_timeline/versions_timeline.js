import { onWillUpdateProps, useComponent, useState } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { serializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { getFieldDomain, useRecordObserver } from "@web/model/relational_model/utils";
import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";

export class VersionsTimeline extends StatusBarField {
    static template = "hr.VersionsTimeline";
    static components = {
        Dropdown,
        DropdownItem,
    };

    /** @override **/
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.state = useState({ openPicker: null });

        if (this.field.type === "many2one") {
            this.specialData = useSpecialDataNoCache((orm, props) => {
                const { foldField, name: fieldName, record } = props;
                const { relation } = record.fields[fieldName];
                const fieldNames = [
                    "display_name",
                    "contract_type_id",
                    "contract_date_start",
                    "contract_date_end",
                ];
                if (foldField) {
                    fieldNames.push(foldField);
                }
                const value = record.data[fieldName];
                let domain = getFieldDomain(record, fieldName, props.domain);
                domain = Domain.and([
                    [["employee_id", "=", props.record.evalContext.id]],
                    domain,
                ]).toList();
                if (domain.length && value) {
                    domain = Domain.or([[["id", "=", value.id]], domain]).toList(
                        record.evalContext
                    );
                }
                return orm.searchRead(
                    relation,
                    domain,
                    fieldNames.filter((fName) => fName in record.fields)
                );
            });
        }

        this.dateTimePickerNewContract = useDateTimePicker({
            target: `datetime-picker-target-new-contract`,
            onApply: async (date) => {
                if (date) {
                    try {
                        await this.tryAndCreateContract(serializeDate(date));
                        this.togglePicker("new", this.dateTimePickerNewContract);
                    } catch (error) {
                        this.dateTimePickerNewContract.state.value = null;
                        this.togglePicker("new", this.dateTimePickerNewContract);
                        throw error;
                    }
                }
            },
            get pickerProps() {
                return { type: "date" };
            },
        });

        this.dateTimePickerAmendContract = useDateTimePicker({
            target: `datetime-picker-target-version`,
            onApply: async (date) => {
                if (date) {
                    try {
                        await this.createVersion(date);
                        this.togglePicker("amend", this.dateTimePickerAmendContract);
                    } catch (error) {
                        this.togglePicker("amend", this.dateTimePickerAmendContract);
                        throw error;
                    }
                }
            },
            get pickerProps() {
                return { type: "date" };
            },
        });
    }

    togglePicker(pickerType, picker) {
        if (this.state.openPicker === pickerType) {
            picker.close();
            this.state.openPicker = null;
        } else {
            if (this.state.openPicker === "new") {
                this.dateTimePickerNewContract.close();
            } else if (this.state.openPicker === "amend") {
                this.dateTimePickerAmendContract.close();
            }
            picker.open();
            this.state.openPicker = pickerType;
        }
    }

    displayContractLines() {
        return ["contract_type_id", "contract_date_start", "contract_date_end"].every(
            (fieldName) => fieldName in this.props.record.fields
        );
    }

    resetOptions() {
        this.state.openPicker = null;
    }

    async loadVersion(version_id) {
        const { record } = this.props;
        await record.save();
        await record.model.load({
            context: {
                ...record.model.env.searchModel.context,
                version_id: version_id,
            },
        });
    }

    // Create contract
    async tryAndCreateContract(date) {
        await this.orm.call("hr.employee", "check_no_existing_contract", [
            [this.props.record.resId],
            date,
        ]);
        const contract = await this.orm.call("hr.employee", "create_contract", [
            [this.props.record.resId],
            date,
        ]);
        await this.loadVersion(contract);
    }

    async onClickNewContractBtn() {
        const { record } = this.props;
        await record.save();
        await this.orm.call("hr.version", "check_contract_finished", [[record.data.version_id.id]]);
        this.togglePicker("new", this.dateTimePickerNewContract);
    }

    // Amend contract
    async createVersion(date) {
        const version_id = await this.orm.call("hr.employee", "create_version", [
            this.props.record.evalContext.id,
            { date_version: date },
        ]);

        await this.loadVersion(version_id);
    }

    /** @override **/
    async selectItem(item) {
        this.loadVersion(item.value);
    }

    /** @override **/
    getAllItems() {
        function format(dateString) {
            return luxon.DateTime.fromISO(dateString).toFormat("MMM dd, yyyy");
        }
        const items = super.getAllItems();
        if (!this.displayContractLines) {
            return items;
        }
        const dataById = new Map(this.specialData.data.map((d) => [d.id, d]));

        const selectedVersion = items.find((item) => item.isSelected)?.value;
        const selectedContractDate = dataById.get(selectedVersion)?.contract_date_start;

        return items.map((item, index) => {
            const itemSpecialData = dataById.get(item.value) || {};
            const contractDateStart = itemSpecialData.contract_date_start;
            let contractDateEnd = itemSpecialData.contract_date_end;
            contractDateEnd = contractDateEnd ? format(contractDateEnd) : _t("Indefinite");
            const contractType = itemSpecialData.contract_type_id?.[1] ?? _t("Contract");
            const toolTip = contractDateStart
                ? `${contractType}: ${format(contractDateStart)} - ${contractDateEnd}`
                : _t("No contract");

            return {
                ...item,
                isCurrentContract: contractDateStart === selectedContractDate,
                isInContract: Boolean(contractDateStart),
                toolTip,
            };
        });
    }
}

export function useSpecialDataNoCache(loadFn) {
    const component = useComponent();
    const orm = component.env.services.orm;

    /** @type {{ data: Record<string, T> }} */
    const result = useState({ data: {} });
    useRecordObserver(async (record, props) => {
        result.data = await loadFn(orm, { ...props, record });
    });
    onWillUpdateProps(async (props) => {
        // useRecordObserver callback is not called when the record doesn't change
        if (props.record.id === component.props.record.id) {
            result.data = await loadFn(orm, props);
        }
    });
    return result;
}

export const versionsTimeline = {
    ...statusBarField,
    component: VersionsTimeline,
    additionalClasses: ["o_field_statusbar", "d-flex", "gap-1"],
};

registry.category("fields").add("versions_timeline", versionsTimeline);
