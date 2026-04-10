import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { _t } from "@web/core/l10n/translation";
import { useEffect } from "@odoo/owl";

export class VersionsTimeline extends StatusBarField {
    static template = "hr.VersionsTimeline";

    /** @override **/
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.dateTimePicker = useDateTimePicker({
            target: `datetime-picker-target-version`,
            onApply: (date) => {
                if (date) {
                    this.createVersion(date);
                }
            },
            get pickerProps() {
                return { type: "date" };
            },
        });

        const { specialDataCaches, hooks } = this.props.record.model;

        const clearCache = () => {
            Object.keys(specialDataCaches).forEach((key) => {
                // Invalidate cache after creating or removing version.
                if (JSON.parse(key)[0] == "hr.version") {
                    delete specialDataCaches[key];
                }
            });
        };

        let first = true; // Skip first execution
        useEffect(() => {
            if (!first) {
                clearCache();
                this.props.record.model.load();
            }
            first = false;
        }, () => [this.props.record.data["versions_count"]]);

        const onRecordSaved = hooks.onRecordSaved;
        hooks.onRecordSaved = async (record, changes) => {
            if (["hr.employee", "hr.version"].includes(record.resModel)) {
                clearCache();
            }
            await onRecordSaved(record, changes);
        };
    }

    /** @override **/
    getDomain(props) {
        return Domain.and([
            super.getDomain(props),
            [["employee_id", "=", props.record.evalContext.id]],
        ]).toList();
    }

    /** @override **/
    getFieldNames(props) {
        const fieldNames = super.getFieldNames(props);
        fieldNames.push("employee_type_id", "contract_date_start", "contract_date_end");
        return fieldNames.filter((fName) => fName in props.record.fields);
    }

    displayContractLines() {
        return ["employee_type_id", "contract_date_start", "contract_date_end"].every(
            (fieldName) => fieldName in this.props.record.fields
        );
    }

    async createVersion(date) {
        await this.props.record.save();
        const version_id = await this.orm.call("hr.employee", "create_version", [
            this.props.record.evalContext.id,
            { date_version: date },
        ]);

        await this.props.record.model.load({
            context: {
                ...this.props.record.model.env.searchModel.context,
                version_id: version_id,
            },
        });
    }

    onClickDateTimePickerBtn() {
        this.dateTimePicker.open();
    }

    /** @override **/
    async selectItem(item) {
        const { record } = this.props;
        await record.save();
        await this.props.record.model.load({
            context: {
                ...this.props.record.model.env.searchModel.context,
                version_id: item.value,
            },
        });
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
            const employeeType = itemSpecialData.employee_type_id?.[1] ?? _t("Contract");
            const toolTip = contractDateStart
                ? `${employeeType}: ${format(contractDateStart)} - ${contractDateEnd}`
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

export const versionsTimeline = {
    ...statusBarField,
    component: VersionsTimeline,
    additionalClasses: ["o_field_statusbar", "d-flex", "gap-1"],
};

registry.category("fields").add("versions_timeline", versionsTimeline);
