import { Component, proxy, t, useProps } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

/**
 * @param {Object} model
 * @param {Object} [actions]
 * @param {Function} [actions.save]
 * @param {Function} [actions.discard]
 * @param {() => Object | null} [actions.getRecord] the record the indicator reflects,
 *  defaults to the root of the model (a list gives its edited record instead)
 */
export function useStatusIndicator(model, actions = {}) {
    const _fieldIsDirty = proxy({ value: false });
    useBus(model.bus, "FIELD_IS_DIRTY", (ev) => {
        _fieldIsDirty.value = ev.detail;
    });

    return {
        props() {
            const record = actions.getRecord ? actions.getRecord() : model.root;
            return {
                isDirty: Boolean(record?.dirty) || _fieldIsDirty.value,
                isValid: record?.isValid ?? true,
                isNew: Boolean(record?.isNew && !record.offlineId),
                save: actions.save,
                discard: actions.discard,
            };
        },
    };
}

export const BaseStatusIndicatorSchema = {
    isDirty: t.boolean(),
    isValid: t.boolean().optional(true),
    isNew: t.boolean().optional(false),
    save: t.function(),
    discard: t.function(),
    onMouseDownDiscard: t.function().optional(),
};

export class FormStatusIndicator extends Component {
    static template = "web.FormStatusIndicator";
    props = useProps(BaseStatusIndicatorSchema);

    get displayButtons() {
        return this.indicatorMode !== "saved";
    }

    get indicatorMode() {
        const { isValid, isNew, isDirty } = this.props;
        if (isNew || isDirty) {
            return isValid ? "dirty" : "invalid";
        }
        return "saved";
    }

    async discard() {
        await this.props.discard();
    }
    async save() {
        await this.props.save();
    }
}
