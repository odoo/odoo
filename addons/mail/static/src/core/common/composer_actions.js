import { Component, toRaw, useEffect, useRef, useState, xml } from "@odoo/owl";
import { EmojiPicker } from "@web/core/emoji_picker/emoji_picker";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markEventHandled } from "@web/core/utils/misc";
import { Action, ACTION_TAGS, useAction, UseActions } from "@mail/core/common/action";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

export const composerActionsRegistry = registry.category("mail.composer/actions");
export const EMOJI_ACTION_ID = "add-emoji";

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("@mail/core/common/action").ActionDefinition} ActionDefinition */
/** @typedef {import("models").Composer} Composer */
/** @typedef {ActionDefinition} ComposerActionDefinition */

/**
 * @param {string} id
 * @param {ComposerActionDefinition} definition
 */
export function registerComposerAction(id, definition) {
    composerActionsRegistry.add(id, definition);
}

registerComposerAction("send-message", {
    btnClass: ({ action }) => (action.isActive ? "o-sendMessageActive o-text-white shadow-sm" : ""),
    condition: ({ composer, owner, store }) =>
        (store.env.isSmall && composer.message) || (!owner.env.inChatter && !composer.message),
    disabledCondition: ({ owner }) => owner.isSendButtonDisabled,
    icon: "fa fa-paper-plane-o",
    isActive: ({ owner }) => owner.sendMessageState.active,
    name: ({ composer, owner }) =>
        composer.message
            ? _t("Save editing")
            : composer.targetThread?.model === "discuss.channel"
            ? _t("Send")
            : owner.props.type === "note"
            ? _t("Log")
            : _t("Send"),
    onSelected: ({ owner }) => owner.sendMessage(),
    setup: ({ owner }) => {
        owner.sendMessageState = useState({ active: false });
        useEffect(
            () => {
                owner.sendMessageState.active = !owner.isSendButtonDisabled;
            },
            () => [owner.isSendButtonDisabled]
        );
    },
    sequenceQuick: 30,
});

export class ComposerPicker extends Component {
    static props = ["*"];
    static template = xml`
        <div t-if="props.pickerActions?.length" class="d-flex flex-column">
            <span class="btn-group"><button class="btn btn-group-item" t-foreach="props.pickerActions" t-as="pickerAction" t-key="pickerAction.id" t-esc="pickerAction.actionPanelName" t-on-click="pickerAction.actionPanelOpen.bind(pickerAction)"/></span>
            <div class="d-flex flex-column"><t t-component="props.component" t-props="props.componentProps"/></div>
        </div>
        <t t-else="" t-component="props.component" t-props="props.componentProps"/>
    `;
}

registerComposerAction(EMOJI_ACTION_ID, {
    actionPanelComponent: EmojiPicker,
    actionPanelName: _t("Emoji"),
    actionPanelOpen({ actions, ev, owner }) {
        if (ev) {
            markEventHandled(ev, "Composer.onClickAddEmoji");
        }
        const pickerActions = actions.actions.filter((act) =>
            act.tags.includes(ACTION_TAGS.COMPOSER_PICKER)
        );
        this.popover?.open(owner.root.el.querySelector(`[name="${this.id}"]`), {
            pickerActions,
            component: EmojiPicker,
            componentProps: {
                onSelect: (emoji) => owner.addEmoji(emoji),
            },
        });
    },
    disabledCondition: ({ owner }) => owner.areAllActionsDisabled,
    icon: "fa fa-smile-o",
    name: _t("Add Emojis"),
    setup({ actions }) {
        const ui = useService("ui");
        this.popover = usePopover(ComposerPicker, {
            arrow: false,
            class: ui.isSmall
                ? "o-mail-Composer-pickerBottomSheet d-flex flex-column p-0 position-relative"
                : undefined,
            onClose: () => {
                const activeAction = actions.actionStack.pop();
                activeAction?.actionPanelClose?.();
                actions.activeAction = null;
            },
            useBottomSheet: ui.isSmall,
        });
    },
    sequenceQuick: 20,
    tags: ACTION_TAGS.COMPOSER_PICKER,
});
registerComposerAction("upload-files", {
    disabledCondition: ({ owner }) => owner.areAllActionsDisabled,
    condition: ({ owner }) => owner.allowUpload,
    icon: "fa fa-paperclip",
    name: _t("Attach Files"),
    onSelected: ({ composer: comp, owner }, ev) => {
        owner.fileUploaderRef.el?.click();
        const composer = toRaw(comp);
        markEventHandled(ev, "composer.clickOnAddAttachment");
        composer.autofocus++;
    },
    setup: ({ owner }) => (owner.fileUploaderRef = useRef("file-uploader")),
    sequence: 20,
});
registerComposerAction("open-full-composer", {
    condition: ({ composer, owner }) =>
        owner.props.showFullComposer &&
        composer.targetThread &&
        composer.targetThread.model !== "discuss.channel" &&
        !owner.env.inFrontendPortalChatter,
    hotkey: "shift+c",
    icon: "fa fa-expand",
    name: _t("Open Full Composer"),
    onSelected: ({ owner }) => owner.onClickFullComposer(),
    sequence: 30,
});
registerComposerAction("add-canned-response", {
    condition: ({ composer, store }) =>
        store.hasCannedResponses &&
        composer.targetThread &&
        store.env.services["mail.suggestion"]
            .getSupportedDelimiters(composer.targetThread)
            .find(([delimiter]) => delimiter === "::"),
    icon: "fa fa-file-text-o",
    name: _t("Insert a Canned response"),
    onSelected: ({ owner }, ev) => owner.onClickInsertCannedResponse(ev),
    sequence: 5,
});

export class ComposerAction extends Action {
    /** @type {() => Composer} */
    composerFn;

    /**
     * @param {Object} param0
     * @param {Composer|() => Composer} composer
     */
    constructor({ composer }) {
        super(...arguments);
        this.composerFn = typeof composer === "function" ? composer : () => composer;
    }

    get params() {
        return Object.assign(super.params, { composer: this.composerFn() });
    }
}

class UseComposerActions extends UseActions {
    ActionClass = ComposerAction;
}

/**
 * @param {Object} [params0={}]
 * @param {Composer|() => Composer} composer
 */
export function useComposerActions({ composer } = {}) {
    const actions = useAction(composerActionsRegistry, UseComposerActions, ComposerAction, {
        composer,
    });
    return actions;
}
