import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { convertCSSColorToRgba } from "@web/core/utils/colors";

function isBgBlurAvailable(target) {
    const backgroundColorOpacity =
        target && convertCSSColorToRgba(getComputedStyle(target).backgroundColor)?.opacity;
    return (
        (backgroundColorOpacity > 0 && backgroundColorOpacity < 100) ||
        target?.style.backgroundImage.includes("rgba") ||
        false
    );
}

export class BgBlurOption extends BaseOptionComponent {
    static template = "website.BgBlurOption";

    props = props({
        // BaseOptionComponent.props was an empty object; applyTo is declared
        // here because this component reads this.props.applyTo.
        applyTo: t.string().optional(),
        level: t.number().optional(2),
    });

    setup() {
        super.setup();
        this.blurState = useDomState((el) => {
            const target = this.props.applyTo ? el.querySelector(this.props.applyTo) : el;
            return {
                show: isBgBlurAvailable(target),
                hasBlur: parseFloat(target?.style.getPropertyValue("--o-bg-blur")) > 0,
            };
        });
    }
}

export class BgBlurAction extends BuilderAction {
    static id = "bgBlur";

    getValue({ editingElement }) {
        // Do not use styleAction for this option. It reads the computed value,
        // but "--o-bg-blur" is registered in CSS with @property and inherits:
        // false. In Chrome, the computed value can then be the "@property
        // initial-value" instead of the inline value set by the option.
        return editingElement.style.getPropertyValue("--o-bg-blur") || "0";
    }

    apply({ editingElement, value }) {
        editingElement.style.setProperty("--o-bg-blur", value);
        editingElement.classList.add("o_bg_blur_option");
    }
}

export class BgBlurOptionPlugin extends Plugin {
    static id = "bgBlurOption";
    resources = {
        builder_actions: {
            BgBlurAction,
        },
        on_bg_color_updated_handlers: this.cleanUnavailableBlur.bind(this),
    };

    cleanUnavailableBlur(editingElement) {
        if (!isBgBlurAvailable(editingElement)) {
            editingElement.style.removeProperty("--o-bg-blur");
            editingElement.classList.remove("o_bg_blur_option", "o_bg_blur_no_enhance");
        }
    }
}

registry.category("website-plugins").add(BgBlurOptionPlugin.id, BgBlurOptionPlugin);
