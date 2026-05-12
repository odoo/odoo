import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { Component, useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

export function useStatusIndicator(model, actions = {}) {
    const _fieldIsDirty = useState({ value: false });
    useBus(model.bus, "FIELD_IS_DIRTY", (ev) => {
        _fieldIsDirty.value = ev.detail;
    });

    return {
        props() {
            const { root } = model;
            return {
                isDirty: root.dirty || _fieldIsDirty.value,
                isValid: root.isValid,
                isNew: root.isNew && !root.offlineId,
                save: actions.save,
                discard: actions.discard,
            };
        },
    };
}

export class FormStatusIndicator extends Component {
    static template = "web.FormStatusIndicator";
    static props = {
        isDirty: Boolean,
        isValid: { type: Boolean, optional: true, default: true },
        isNew: { type: Boolean, optional: true, default: false },
        save: Function,
        discard: Function,
    };

    static defaultProps = {
        isValid: true,
        isNew: false,
    };

    setup() {
        this.saveButton = useRef("save");
        useLayoutEffect(
            () => {
                if (!this.props.isNew && this.indicatorMode === "invalid") {
                    this.saveButton.el.setAttribute("disabled", "1");
                } else {
                    this.saveButton.el.removeAttribute("disabled");
                }
            },
            () => [this.props.isValid, this.props.isDirty]
        );
    }

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
