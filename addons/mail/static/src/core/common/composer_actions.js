import { VoiceRecorder } from "@mail/discuss/voice_message/common/voice_recorder";
import { useComponent, useRef, useState } from "@odoo/owl";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markEventHandled } from "@web/core/utils/misc";

export const composerActionsRegistry = registry.category("discuss.composer/actions");

composerActionsRegistry
    .add("add-emoji", {
        label: _t("Add an Emoji"),
        icon: "fa fa-smile-o",
        select(comp, ev) {
            markEventHandled(ev, "Composer.onClickAddEmoji");
            comp.emojiPicker.toggle({ el: ev.target });
            this.isActive = !this.isActive;
        },
        sequence: 10,
        setup() {
            const comp = useComponent();
            comp.emojiPicker = useEmojiPicker(
                undefined,
                {
                    onSelect: (emoji) => comp.addEmoji(emoji),
                    onClose: () => {
                        if (!comp.ui.isSmall) {
                            comp.props.composer.autofocus++;
                            this.isActive = false;
                        }
                    },
                },
                { arrow: false }
            );
        },
    })
    // .add("add-gif", {
    //     label: _t("Add a GIF"),
    //     icon: "oi oi-gif-picker",
    //     select: (component) => component.onClickAddGif(),
    //     sequence: 15,
    // })
    .add("attach-files", {
        condition: (component) => component.allowUpload,
        label: _t("Attach files"),
        icon: "fa fa-paperclip",
        select: (component) => component.attachFilesRef.el?.click(),
        sequence: 20,
        setup() {
            const comp = useComponent();
            comp.attachFilesRef = useRef("upload-file");
        },
    })
    .add("full-composer", {
        condition: (component) =>
            component.showFullComposer &&
            component.thread &&
            component.thread.model !== "discuss.channel",
        label: _t("Open full composer"),
        icon: "fa fa-expand",
        select: (component) => component.onClickFullComposer(),
        sequence: 30,
    })
    .add("voice-message", {
        component: VoiceRecorder,
        componentProps(component) {
            return {
                composer: component.props.composer,
                initialRecording: true,
                attachmentUploader: component.attachmentUploader,
                onchangeRecording: (recording) => {
                    component.recordingState.recording = !recording;
                    this.isActive = recording;
                },
            };
        },
        condition: (component) =>
            component.thread?.model === "discuss.channel" && component.allowUpload,
        label: _t("Voice message"),
        icon: "fa fa-microphone",
        select() {
            this.isActive = !this.isActive;
        },
        sequence() {
            return this.isActive ? 10 : 35;
        },
        setup() {
            const comp = useComponent();
            comp.recordingState = useState({ recording: false });
        },
    });
// .add("send", {
//     condition: (component) => !component.extended || component.props.composer.message,
//     label: (component) => component.SEND_TEXT,
//     icon: "fa fa-paper-plane-o",
//     select: (component) => component.sendMessage(),
//     sequence: 40,
// });

function transformAction(component, id, action) {
    return {
        id,
        /** Optional component that should be displayed in the view when this action is active. */
        component: action.component,
        /** Condition to display the component of this action. */
        get componentCondition() {
            return this.isActive && this.component && this.condition;
        },
        /** Props to pass to the component of this action. */
        get componentProps() {
            return action.componentProps?.call(this, component);
        },
        /** Condition to display this action */
        get condition() {
            return action.condition?.(component) ?? true;
        },
        isActive: false,
        /** Label of this action, displayed to the user */
        get label() {
            return typeof action.label === "function" ? action.label(component) : action.label;
        },
        /** Icon for the button of this action */
        get icon() {
            return typeof action.icon === "function" ? action.icon(component) : action.icon;
        },
        /**  Action to execute when this action is selected */
        select(ev) {
            action.select.call(this, component, ev);
        },
        /** Determines the order of this action (smaller first) */
        get sequence() {
            return typeof action.sequence === "function"
                ? action.sequence.call(this, component)
                : action.sequence;
        },
        /** Component setup to execute when this action is registered. */
        setup: action.setup,
    };
}

export function useComposerActions() {
    const component = useComponent();
    const state = useState({ actions: [] });
    state.actions = composerActionsRegistry
        .getEntries()
        .map(([id, action]) => transformAction(component, id, action));
    for (const action of state.actions) {
        if (action.setup) {
            action.setup(action);
        }
    }
    return {
        get all() {
            const actions = state.actions
                .filter((action) => action.condition)
                .sort((a1, a2) => a1.sequence - a2.sequence);
            actions.forEach((a) => void a.sequence);
            return actions;
        },
    };
}
