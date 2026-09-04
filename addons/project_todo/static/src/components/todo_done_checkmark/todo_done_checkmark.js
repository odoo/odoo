import { onMounted, useProps, proxy, t, useEffect } from "@odoo/owl";
import { useAnimationMark } from "@web/core/utils/animation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { StateSelectionField, stateSelectionField } from "@web/views/fields/state_selection/state_selection_field";

/** Length of the pop and its halo, as timed by `todo_done_checkmark.scss`. */
const DONE_ANIMATION_DURATION = 500;

export class TodoDoneCheckmark extends StateSelectionField {
    static template = "project_todo.TodoDoneCheckmark";
    props = useProps({
        ...standardFieldProps,
        showLabel: t.boolean().optional(true),
        withCommand: t.boolean().optional(),
        viewType: t.string().optional(),
    });
    setup() {
        super.setup();
        this.uiService = useService("ui");
        this.stateDone = proxy({
            isDone: false, //This state determines the appearance of the done checkmark and should only be actualized when the mouse leaves it (and atfer the form is loaded)
            notReloadState: false, //used to avoid a change of the checkmark when re-rendering the form
        });
        // Keyed on the click, not on `isDone`: that state is withheld while
        // the cursor stays on the checkmark, so the pop would land on the
        // mouse leaving instead of on the click.
        this.justDone = useAnimationMark(DONE_ANIMATION_DURATION);
        onMounted(() => {
            const fieldValue = this.props.record.data[this.props.name]
            this.notDoneState = fieldValue == '1_done' ? '01_in_progress' : fieldValue;
        });
        useEffect(() => {
            if (!this.stateDone.notReloadState) {
                this.stateDone.isDone = this.props.record.data[this.props.name] == '1_done';
            }
        });
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    actualizeDoneState(ev) {
        // Writing the record re-renders the checkmark, which displaces it under
        // a motionless cursor: the browser then emits a mouseleave immediately
        // followed by a mouseover, and thawing on the first would let the state
        // through while the pointer is still there. Asking what actually sits
        // under the pointer tells the two apart with no delay to sit out.
        const under = ev.currentTarget.ownerDocument.elementFromPoint(ev.clientX, ev.clientY);
        if (under && ev.currentTarget.contains(under)) {
            return;
        }
        this.stateDone.notReloadState = false;
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    freezeDoneState(ev) {
        this.stateDone.notReloadState = true;
    }

    /** @private */
    async onDoneToggled() {
        const value = this.props.record.data[this.props.name] != '1_done' ? '1_done' : this.notDoneState;
        if (value == '1_done') {
            this.justDone.mark();
        }
        if (['card', 'list'].includes(this.props.viewType)) {
            await super.updateRecord(value);
        }
        else {
            await this.props.record.update({
                [this.props.name]: value,
            });
        }
    }
}

export const todoDoneCheckmark = {
    ...stateSelectionField,
    component: TodoDoneCheckmark,
    extractProps: (fieldInfo, dynamicInfo) => {
        const props = stateSelectionField.extractProps(fieldInfo, dynamicInfo);
        props.viewType = fieldInfo.viewType;
        return props;
    },
}

registry.category("fields").add("todo_done_checkmark", todoDoneCheckmark);
