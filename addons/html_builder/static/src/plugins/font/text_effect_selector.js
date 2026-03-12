import { useChildSubEnv, useRef, useState } from "@web/owl2/utils";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { DependencyManager } from "@html_builder/core/dependency_manager";
import { useDomState } from "@html_builder/core/utils";
import { InputConfirmationDialog } from "@html_builder/snippets/input_confirmation_dialog";
import { TextEffectUtil } from "./text_effect_util";

export class TextEffectOption extends BaseOptionComponent {
    static template = "html_builder.TextEffectOption";
    static props = {
        onReset: Function,
        showLettersOnly: Boolean,

        // Popover service
        close: { type: Function, optional: true },
    };
    static dependencies = ["builderActions"];
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            presets: this.getPresets(),
            showBack: false,
        });
        this.domState = useDomState(async (editingElement) => ({
            showPresets: !this.getEffectParam(editingElement, "preset"),
            presetName: this.getPresetName(editingElement),
            hasOutline: this.hasOutline(editingElement),
            hasTrail: this.hasTrail(editingElement),
            hasTilt: this.hasTilt(editingElement, "X") || this.hasTilt(editingElement, "Y"),
            effect: editingElement.dataset.textEffect,
            hasShadowPart: this.hasPart(editingElement, "shadow"),
            hasOutlinePart: this.hasPart(editingElement, "outline"),
            hasTrailPart: this.hasPart(editingElement, "trail"),
            hasGeometryPart: this.hasPart(editingElement, "geometry"),
        }));
    }
    getEffectParam(editingElement, paramName) {
        const { getAction } = this.dependencies.builderActions;
        return getAction("updateTextEffect").getValue({
            editingElement,
            params: {
                mainParam: paramName,
            },
        });
    }
    getPresetName(editingElement) {
        const value = this.getEffectParam(editingElement, "preset");
        if (!value) {
            return _t("Custom");
        }
        let preset = this.state.presets.find((preset) => preset.id === value);
        if (preset) {
            return preset.name;
        }
        const idHead = value.match(/\D+/)[0];
        preset = this.state.presets.find((preset) => preset.id === idHead);
        return preset?.name || _t("Custom");
    }
    hasOutline(editingElement) {
        const styleActionValue = this.getEffectParam(editingElement, "outline");
        const values = (styleActionValue || "0").match(/\d+/g);
        return values.some((value) => parseInt(value) > 0);
    }
    hasTrail(editingElement) {
        const styleActionValue = this.getEffectParam(editingElement, "trailCount");
        const values = (styleActionValue || "0").match(/\d+/g);
        return values.some((value) => parseInt(value) > 0);
    }
    hasTilt(editingElement, axis) {
        const styleActionValue = this.getEffectParam(editingElement, `tilt${axis}`);
        const values = (styleActionValue || "0").match(/\d+/g);
        return values.some((value) => parseInt(value) > 0);
    }
    hasPart(editingElement, part) {
        const value = this.getEffectParam(editingElement, "preset");
        if (!value) {
            return true;
        }
        const idHead = value.match(/\D+/)[0];
        if (idHead === "custom") {
            return true;
        }
        const rootPreset = this.state.presets.find((preset) => preset.id === idHead);
        const keys = Object.keys(rootPreset.effect);
        const regex = {
            shadow: /^shadow/,
            outline: /^outline/,
            trail: /^trail/,
            geometry: /^(rotate|tilt|skew|move|scale)/,
        }[part];
        return keys.some((key) => regex.test(key));
    }
    getPresets() {
        const savedPresets = JSON.parse(window.localStorage.getItem("textEffectPresets") || "[]");
        const presets = [
            ...savedPresets,
            {
                id: "outline",
                name: _t("Outline"),
                effect: {
                    outline: "2px",
                    outlineColor: "#808080",
                },
            },
            {
                id: "sharp",
                name: _t("Sharp Shadow"),
                effect: { shadowBlur: "1px" },
            },
            {
                id: "blurred",
                name: _t("Blurred Shadow"),
                effect: { shadowBlur: "10px" },
            },
            {
                id: "glow",
                name: _t("Glow"),
                effect: {
                    shadowBlur: "10px",
                    shadowColor: "#3dd5f3",
                    shadowOffsetX: "0px",
                    shadowOffsetY: "0px",
                },
            },
            {
                id: "trail",
                name: _t("Trail Art"),
                effect: {
                    trailCount: "10",
                    trailOffsetX: "30px",
                    trailOffsetY: "30px",
                    skewX: "-15deg",
                },
            },
            {
                id: "warp",
                name: _t("Warp"),
                effect: {
                    trailCount: "3",
                    trailOffsetX: "0px",
                    trailOffsetY: "-10px",
                    trailStartColor: "var(--600)",
                    trailEndColor: "var(--white)",
                },
            },
            {
                id: "ribbon",
                name: _t("Ribbon"),
                effect: {
                    shadowBlur: "10px",
                    shadowColor: "#FFFFFF",
                    shadowOffsetX: "0px",
                    shadowOffsetY: "0px",
                    outline: "2px",
                    outlineColor: "#FF0000",
                    rotate: "-10deg",
                },
            },
            {
                id: "speed",
                name: _t("Speed"),
                effect: {
                    trailCount: "10",
                    trailOffsetX: "-30px",
                    trailOffsetY: "0px",
                    trailStartColor: "#ED452F",
                    trailEndColor: "#FFFEB2",
                    skewX: "-15deg",
                },
            },
        ];
        for (const preset of presets) {
            preset.effect.preset = preset.id;
            preset.effectJson = JSON.stringify(preset.effect);
            const el = document.createElement("span");
            el.dataset.textEffect = preset.effectJson;
            TextEffectUtil.applyConfiguredEffects(el);
            preset.effectStyle = el.getAttribute("style");
            if (preset.effectStyle?.includes("-webkit") || this.props.showLettersOnly) {
                preset.sampleText = "A";
            } else {
                preset.sampleText = "\uD83E\uDD84";
            }
            if (/\d+$/.test(preset.id)) {
                preset.isCustom = true;
            }
        }
        return presets;
    }
    onClickOpenPresets() {
        this.domState.showPresets = true;
        this.state.showBack = true;
    }
    onClickClosePresets() {
        this.domState.showPresets = false;
        this.state.showBack = false;
    }
    onClickSavePreset() {
        this.dialog.add(InputConfirmationDialog, {
            title: _t("Save text effect preset"),
            inputLabel: _t("Name"),
            defaultValue: _t("My custom effect"),
            confirmLabel: _t("Save"),
            confirm: (inputValue) => {
                const json = JSON.parse(this.domState.effect || "{}");
                const savedPresets = JSON.parse(
                    window.localStorage.getItem("textEffectPresets") || "[]"
                );
                function generateId() {
                    const idHead = (json.preset || "custom").match(/\D+/)[0];
                    let count = 1;
                    while (count > 0) {
                        const id = `${idHead}${count}`;
                        if (savedPresets.every((preset) => preset.id !== id)) {
                            return id;
                        }
                        count++;
                    }
                }
                savedPresets.unshift({
                    id: generateId(),
                    name: inputValue,
                    effect: json,
                });
                window.localStorage.setItem("textEffectPresets", JSON.stringify(savedPresets));
                this.notification.add(_t("Custom effect saved"), {
                    type: "info",
                });
                this.state.presets = this.getPresets();
            },
            cancel: () => {},
        });
    }
    onClickRemovePreset(presetId) {
        const savedPresets = JSON.parse(window.localStorage.getItem("textEffectPresets") || "[]");
        const filteredPresets = savedPresets.filter((preset) => preset.id !== presetId);
        window.localStorage.setItem("textEffectPresets", JSON.stringify(filteredPresets));
        this.notification.add(_t("Custom effect removed"), {
            type: "info",
        });
        this.state.presets = this.getPresets();
    }
    onClickReset() {
        this.props.onReset();
    }
}

export class TextEffectSelector extends Component {
    static template = "html_builder.TextEffectSelector";
    static props = {
        ...toolbarButtonProps,
        config: {
            type: Object,
            shape: { editor: Object, editorBus: Object },
        },
        getTextEffectOrCreateDefault: Function,
        getState: Function,
        updateState: Function,
    };

    setup() {
        this.props.updateState();
        this.state = this.props.getState();
        this.root = useRef("root");
        useChildSubEnv({
            dependencyManager: new DependencyManager(),
            getEditingElement: () => this.activeElement,
            getEditingElements: () => (this.activeElement ? [this.activeElement] : []),
            weContext: {},
            editor: this.props.config.editor,
            editorBus: this.props.config.editorBus,
            services: this.props.config.editor.services,
        });
        this.popover = usePopover(TextEffectOption, {
            env: this.__owl__.childEnv,
            onClose: () => {
                if (this.activeElement && this.activeElement.dataset.textEffect) {
                    const json = JSON.parse(this.activeElement.dataset.textEffect);
                    if (!json.preset) {
                        this.onReset?.(this.activeElement);
                        delete this.onReset;
                    }
                }
                if (!this.props.config.editor.isDestroyed) {
                    this.props.updateState();
                }
            },
        });
    }

    onClick(ev) {
        if (this.popover.isOpen) {
            this.popover.close();
            return;
        }
        const { element, onReset } = this.props.getTextEffectOrCreateDefault();
        if (!element) {
            return;
        }
        this.activeElement = element;
        this.onReset = onReset;

        this.props.updateState();
        this.popover.open(this.root.el, {
            onReset: () => {
                onReset(this.activeElement);
                this.popover.close();
            },
            showLettersOnly: !ev.shiftKey,
        });
    }
}
