import { useSubEnv } from "@web/owl2/utils";
import { Component, onWillUnmount, proxy, useProps, t, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
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
    makeTextEffectCustom,
    removeShadow,
} from "./text_effect_util";

const DEFAULT_TEXT_EFFECT = {
    preset: "blurred_black",
    shadows: [
        {
            shadowBlur: "10px",
        },
    ],
};

/**
 * Presets as tiles, then one row per shadow and the outline, on one page.
 * Nothing is applied until a preset is picked or a shadow is added.
 */
export class TextEffectOption extends BaseOptionComponent {
    static template = "html_builder.TextEffectOption";

    setup() {
        super.setup();
        const editingElement = this.env.getEditingElement();
        this.state = proxy({
            hasElement: !!editingElement,
        });
        // Read again after each edit, the rows of the builder included: an
        // edited preset becomes a custom one, offered and marked as current.
        this.domState = useDomState(async (editingElement) => ({
            presets: this.getPresets(),
            appliedPreset: this.getAppliedPreset(editingElement),
            hasOutline: this.hasOutline(editingElement),
            shadowIndexes: this.getShadowIndexes(editingElement),
        }));
        if (!editingElement) {
            // Nothing to read yet: the presets are offered to apply one.
            this.domState.presets = this.getPresets();
        }
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
        const customPresets = [
            // Custom effects of this editing session that a preset replaced,
            // first: they are older than the ones still on the page.
            ...(this.env.getRememberedTextEffects?.() || []),
            ...[...this.document.querySelectorAll("#wrap span[data-text-effect]")].map((el) =>
                JSON.parse(el.dataset.textEffect)
            ),
        ]
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
        ];
        for (const preset of presets) {
            if (!preset.isCustom && preset.id !== "no_shadow") {
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
        makeTextEffectCustom(textEffect);
        editingElement.dataset.textEffect = JSON.stringify(textEffect);
        applyConfiguredEffects(editingElement);
        this.domState.shadowIndexes = this.getShadowIndexes(editingElement);
        this.domState.hasOutline = this.hasOutline(editingElement);
        this.domState.presets = this.getPresets();
        this.domState.appliedPreset = this.getAppliedPreset(editingElement);
        this.env.editor.shared.history.commit();
    }
    onClickAddShadow() {
        if (!this.env.getEditingElement()) {
            const textEffect = { preset: "custom" };
            addShadow(textEffect);
            this.onSelectedTextEffect(JSON.stringify(textEffect));
            return;
        }
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
        const { element: editingElement, activePreset } = this.env.applyTextEffect(effectJson);
        this.domState.presets = this.getPresets();
        this.domState.appliedPreset = activePreset;
        this.state.hasElement = !!editingElement;
        if (editingElement) {
            this.domState.shadowIndexes = this.getShadowIndexes(editingElement);
            this.domState.hasOutline = this.hasOutline(editingElement);
        }
    }
}

/**
 * Text effects as a section of the Effects panel (see effects_panel_sections).
 */
export class TextEffectSection extends Component {
    static template = xml`<TextEffectOption/>`;
    static components = { TextEffectOption };
    props = useProps({
        config: t.object({ editor: t.object(), editorBus: t.object() }),
        prepareTextEffectSelection: t.function(),
        applyTextEffect: t.function(),
        previewTextEffect: t.function(),
        revertTextEffect: t.function(),
        getRememberedEffects: t.function(),
        updateState: t.function(),
    });

    setup() {
        this.activeElement = this.props.prepareTextEffectSelection().element;
        useSubEnv({
            dependencyManager: new DependencyManager(),
            getEditingElement: () => this.activeElement,
            getEditingElements: () => (this.activeElement ? [this.activeElement] : []),
            applyTextEffect: (effectJson) => {
                const state = this.props.applyTextEffect(effectJson);
                this.activeElement = state.element;
                return state;
            },
            previewTextEffect: (effectJson) => this.props.previewTextEffect(effectJson),
            revertTextEffect: () => this.props.revertTextEffect(),
            getRememberedTextEffects: () => this.props.getRememberedEffects(),
            weContext: {},
            editor: this.props.config.editor,
            editorBus: this.props.config.editorBus,
            services: this.props.config.editor.services,
        });
        onWillUnmount(() => {
            this.props.revertTextEffect();
            if (!this.props.config.editor.isDestroyed) {
                this.props.updateState();
            }
        });
    }
}
