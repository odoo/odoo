import { useSubEnv } from "@web/owl2/utils";
import { Component, onWillUnmount, useProps, t, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { DependencyManager } from "@html_builder/core/dependency_manager";
import { useDomState } from "@html_builder/core/utils";
import {
    addShadow,
    applyConfiguredEffects,
    getShadowCount,
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
 * Presets as tiles, the last one "Custom": a custom effect shows one row per
 * shadow and the outline. Nothing is applied until a tile is picked.
 */
export class TextEffectOption extends BaseOptionComponent {
    static template = "html_builder.TextEffectOption";

    setup() {
        super.setup();
        const editingElement = this.env.getEditingElement();
        // Read again after each edit, the rows of the builder included.
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
        ];
        for (const preset of presets) {
            if (preset.id !== "no_shadow") {
                preset.effect.preset = preset.id;
            }
            preset.effectJson = JSON.stringify(preset.effect);
            Object.assign(preset, this.getEffectPreview(preset.effectJson));
        }
        return presets;
    }
    /**
     * A custom effect: none of the presets.
     */
    get isCustom() {
        const appliedPreset = this.domState.appliedPreset;
        return (
            !!appliedPreset &&
            !(this.domState.presets || []).some((preset) => preset.id === appliedPreset)
        );
    }
    /**
     * The last custom effect of this editing session, or else one the page
     * uses: the Custom tile brings it back.
     */
    getLastCustomEffect() {
        const pageEffect = [...this.document.querySelectorAll("#wrap span[data-text-effect]")]
            .map((el) => JSON.parse(el.dataset.textEffect))
            .find(
                (textEffect) =>
                    textEffect.preset === "custom" && hasConfiguredTextEffect(textEffect)
            );
        return this.env.getLastCustomTextEffect?.() || pageEffect;
    }
    /**
     * The Custom tile is the custom effect of the user: the last one, else the
     * current preset to start from, else one shadow.
     */
    onClickCustom() {
        if (this.isCustom) {
            return;
        }
        const editingElement = this.env.getEditingElement();
        const textEffect = editingElement ? this.getTextEffect(editingElement) : {};
        let customEffect = this.getLastCustomEffect();
        if (!customEffect && hasConfiguredTextEffect(textEffect)) {
            customEffect = { ...textEffect, preset: "custom" };
        }
        if (!customEffect) {
            customEffect = { preset: "custom" };
            addShadow(customEffect);
        }
        this.onSelectedTextEffect(JSON.stringify(customEffect));
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
        const remainingEffect = this.getTextEffect(this.env.getEditingElement());
        removeShadow(remainingEffect, shadowIndex);
        if (!hasConfiguredTextEffect(remainingEffect)) {
            // Nothing would be left: the text has no effect, as after "No
            // Shadow", and the Custom tile does not bring the shadow back.
            this.onSelectedTextEffect("{}", { keepReplaced: false });
            return;
        }
        this.updateTextEffect((textEffect) => removeShadow(textEffect, shadowIndex));
    }
    onPreviewTextEffect(effectJson) {
        this.env.previewTextEffect(effectJson);
    }
    restoreTextEffectPreview() {
        this.env.revertTextEffect();
    }
    onSelectedTextEffect(effectJson, options) {
        const { element: editingElement, activePreset } = this.env.applyTextEffect(
            effectJson,
            options
        );
        this.domState.presets = this.getPresets();
        this.domState.appliedPreset = activePreset;
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
        getLastCustomEffect: t.function(),
        updateState: t.function(),
    });

    setup() {
        this.activeElement = this.props.prepareTextEffectSelection().element;
        useSubEnv({
            dependencyManager: new DependencyManager(),
            getEditingElement: () => this.activeElement,
            getEditingElements: () => (this.activeElement ? [this.activeElement] : []),
            applyTextEffect: (effectJson, options) => {
                const state = this.props.applyTextEffect(effectJson, options);
                this.activeElement = state.element;
                return state;
            },
            previewTextEffect: (effectJson) => this.props.previewTextEffect(effectJson),
            revertTextEffect: () => this.props.revertTextEffect(),
            getLastCustomTextEffect: () => this.props.getLastCustomEffect(),
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
