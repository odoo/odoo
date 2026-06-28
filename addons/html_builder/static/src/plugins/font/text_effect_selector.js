import { useChildSubEnv } from "@web/owl2/utils";
import { Component, proxy } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownCloser, useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { DependencyManager } from "@html_builder/core/dependency_manager";
import { useDomState } from "@html_builder/core/utils";
import {
    addShadow,
    applyConfiguredEffects,
    getShadowCount,
    getTextEffectPresetHash,
    getTextEffectPresetId,
    hasConfiguredTextEffect,
    removeShadow,
    updateTextEffectPresetHash,
} from "./text_effect_util";

const DEFAULT_TEXT_EFFECT = {
    preset: "blurred_black",
    shadows: [
        {
            shadowBlur: "10px",
        },
    ],
};

export class TextEffectOption extends BaseOptionComponent {
    static template = "html_builder.TextEffectOption";
    static components = { DropdownItem };

    setup() {
        super.setup();
        const editingElement = this.env.getEditingElement();
        this.state = proxy({
            presets: this.getPresets(),
            showPresetDropdown: !editingElement || !this.isCustom(editingElement),
            appliedPreset: editingElement ? this.getAppliedPreset(editingElement) : undefined,
        });
        this.dropdownControl = useDropdownCloser();
        this.domState = useDomState(async (editingElement) => {
            if (!editingElement) {
                return {
                    hasOutline: false,
                    shadowIndexes: [],
                };
            }
            return {
                hasOutline: this.hasOutline(editingElement),
                shadowIndexes: this.getShadowIndexes(editingElement),
            };
        });
    }
    isCustom(editingElement) {
        return this.getTextEffect(editingElement).preset === "custom";
    }
    getTextEffect(editingElement) {
        return JSON.parse(editingElement.dataset.textEffect || "{}");
    }
    getAppliedPreset(editingElement) {
        return getTextEffectPresetId(this.getTextEffect(editingElement));
    }
    getShadowCount(editingElement) {
        return getShadowCount(this.getTextEffect(editingElement));
    }
    getShadowIndexes(editingElement) {
        return Array.from({ length: this.getShadowCount(editingElement) }, (_, index) => index);
    }
    hasOutline(editingElement) {
        const values = (this.getTextEffect(editingElement).outline || "0").match(/\d+/g);
        return values.some((value) => parseInt(value) > 0);
    }
    getPresets() {
        const customPresetIds = new Set();
        const customPresets = [...this.document.querySelectorAll("#wrap span[data-text-effect]")]
            .map((el) => JSON.parse(el.dataset.textEffect))
            .filter(
                (textEffect) =>
                    textEffect.preset === "custom" && hasConfiguredTextEffect(textEffect)
            )
            .reduce((presets, textEffect) => {
                const presetHash = textEffect.presetHash || getTextEffectPresetHash(textEffect);
                if (customPresetIds.has(presetHash)) {
                    return presets;
                }
                customPresetIds.add(presetHash);
                presets.push({
                    id: presetHash,
                    name: _t("Custom Shadow"),
                    isCustom: true,
                    effect: { ...textEffect, presetHash },
                });
                return presets;
            }, []);
        const presets = [
            {
                id: "no_shadow",
                name: _t("No Shadow"),
                effect: {},
            },
            {
                id: "blurred_black",
                name: _t("Blurred (Black)"),
                effect: DEFAULT_TEXT_EFFECT,
            },
            {
                id: "blurred_white",
                name: _t("Blurred (White)"),
                previewBackground: "dark",
                effect: {
                    shadows: [
                        {
                            shadowColor: "rgba(255, 255, 255, 0.5)",
                            shadowBlur: "10px",
                        },
                    ],
                },
            },
            {
                id: "outline",
                name: _t("Outline"),
                effect: {
                    outline: "2px",
                    outlineColor: "var(--o-color-1)",
                },
            },
            {
                id: "flat",
                name: _t("Flat"),
                effect: {
                    shadows: [
                        {
                            shadowBlur: "1px",
                        },
                    ],
                },
            },
            {
                id: "glow",
                name: _t("Glow"),
                effect: {
                    shadows: [
                        {
                            shadowBlur: "1px",
                            shadowColor: "#FFFFFF",
                            shadowOffsetX: "0px",
                            shadowOffsetY: "0px",
                        },
                        {
                            shadowBlur: "2px",
                            shadowColor: "var(--o-color-1)",
                            shadowOffsetX: "0px",
                            shadowOffsetY: "0px",
                        },
                        {
                            shadowBlur: "8px",
                            shadowColor: "var(--o-color-1)",
                            shadowOffsetX: "0px",
                            shadowOffsetY: "0px",
                        },
                    ],
                },
            },
            ...customPresets,
            {
                id: "custom",
                name: _t("Custom"),
                effect: {
                    preset: "custom",
                },
            },
        ];
        for (const preset of presets) {
            if (!preset.isCustom && preset.id !== "no_shadow" && preset.id !== "custom") {
                preset.effect.preset = preset.id;
            }
            preset.effectJson = JSON.stringify(preset.effect);
            Object.assign(preset, this.getEffectPreview(preset.effectJson));
        }
        return presets;
    }
    getEffectPreview(effectJson) {
        const el = this.document.createElement("span");
        el.dataset.textEffect = effectJson;
        applyConfiguredEffects(el);
        const effectStyle = el
            .getAttribute("style")
            ?.replaceAll(/var\(--(o-color-\d+)\)/g, "var(--hb-cp-$1)");
        return {
            effectStyle,
        };
    }
    onClickBack() {
        this.state.presets = this.getPresets();
        const editingElement = this.env.getEditingElement();
        this.state.appliedPreset = editingElement
            ? this.getAppliedPreset(editingElement)
            : undefined;
        this.state.showPresetDropdown = true;
    }
    async updateTextEffect(mutator) {
        const editingElement = this.env.getEditingElement();
        if (!editingElement) {
            return;
        }
        const textEffect = this.getTextEffect(editingElement);
        const didUpdate = mutator(textEffect);
        if (didUpdate === false) {
            return;
        }
        updateTextEffectPresetHash(textEffect);
        editingElement.dataset.textEffect = JSON.stringify(textEffect);
        applyConfiguredEffects(editingElement);
        this.domState.shadowIndexes = this.getShadowIndexes(editingElement);
        this.domState.hasOutline = this.hasOutline(editingElement);
        this.state.presets = this.getPresets();
        this.state.appliedPreset = this.getAppliedPreset(editingElement);
        this.env.editor.shared.history.commit();
    }
    onClickAddShadow() {
        this.updateTextEffect((textEffect) => addShadow(textEffect));
    }
    onClickRemoveShadow(shadowIndex) {
        this.updateTextEffect((textEffect) => removeShadow(textEffect, shadowIndex));
    }
    onPreviewTextEffect(effectJson) {
        this.env.previewTextEffect(effectJson);
    }
    restoreTextEffectPreview() {
        this.env.revertTextEffect();
    }
    onSelectedTextEffect(effectJson) {
        const effect = JSON.parse(effectJson);
        const isCustom = effect.preset === "custom";
        const { element: editingElement, activePreset } = this.env.applyTextEffect(effectJson);
        this.state.presets = this.getPresets();
        this.state.appliedPreset = activePreset;
        if (editingElement) {
            this.domState.shadowIndexes = this.getShadowIndexes(editingElement);
            this.domState.hasOutline = this.hasOutline(editingElement);
        }
        this.state.showPresetDropdown = !isCustom;
        if (!isCustom) {
            this.dropdownControl.close();
        }
    }
}

export class TextEffectSelector extends Component {
    static template = "html_builder.TextEffectSelector";
    static components = { Dropdown, TextEffectOption };
    static props = {
        ...toolbarButtonProps,
        config: {
            type: Object,
            shape: { editor: Object, editorBus: Object },
        },
        prepareTextEffectSelection: Function,
        applyTextEffect: Function,
        previewTextEffect: Function,
        revertTextEffect: Function,
        getState: Function,
        updateState: Function,
    };

    setup() {
        this.props.updateState();
        this.state = this.props.getState();
        this.dropdown = useDropdownState({
            onClose: () => this.onCloseDropdown(),
        });
        useChildSubEnv({
            dependencyManager: new DependencyManager(),
            getEditingElement: () => this.activeElement,
            getEditingElements: () => (this.activeElement ? [this.activeElement] : []),
            applyTextEffect: (effectJson) => this.applyTextEffect(effectJson),
            previewTextEffect: (effectJson) => this.props.previewTextEffect(effectJson),
            revertTextEffect: () => this.props.revertTextEffect(),
            weContext: {},
            editor: this.props.config.editor,
            editorBus: this.props.config.editorBus,
            services: this.props.config.editor.services,
        });
    }

    onClickTextEffect() {
        if (this.state.isDisabled) {
            return;
        }
        if (this.dropdown.isOpen) {
            this.dropdown.close();
            return;
        }
        let state = this.props.prepareTextEffectSelection();
        if (!state.hasTextEffect) {
            state = this.props.applyTextEffect(JSON.stringify(DEFAULT_TEXT_EFFECT));
        }
        this.activeElement = state.element;
        this.dropdown.open();
    }

    applyTextEffect(effectJson) {
        const state = this.props.applyTextEffect(effectJson);
        this.activeElement = state.element;
        return state;
    }

    onCloseDropdown() {
        this.props.revertTextEffect();
        this.activeElement = undefined;
        if (!this.props.config.editor.isDestroyed) {
            this.props.updateState();
        }
    }
}
