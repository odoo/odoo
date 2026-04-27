/** @odoo-module */

import { Component } from "@odoo/owl";
import { user } from "@web/core/user";
import { FileInput } from "@web/core/file_input/file_input";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { _t } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";

export class RainbowEffect extends Component {
    static template = "web_studio.ViewEditorSidebar.RainbowEffect";
    static props = {
        effect: { type: true, optional: true },
        onChange: { type: Function },
    };
    static components = {
        FileInput,
        SelectMenu,
        Property,
    };
    setup() {
        this.user = user;
    }
    get choices() {
        return [
            { label:  _t("Fast"), value: "fast" },
            { label:  _t("Medium"), value: "medium" },
            { label:  _t("Slow"), value: "slow" },
            { label:  _t("None"), value: "no" },
        ];
    }
    get rainbowEffect() {
        const effect = this.props.effect;
        if (effect === undefined) {
            return null;
        }
        if (effect === "True") {
            return {};
        }
        return evaluateExpr(effect);
    }
    onRainbowEffectChange(name, value) {
        const effect = this.rainbowEffect;
        if (!value || !value.length) {
            delete effect[name];
        } else {
            effect[name] = value;
        }
        this.props.onChange(effect, "effect");
    }
    toggleRainbowMan() {
        const effect = this.rainbowEffect;
        const newValue = effect ? "False" : "{}";
        this.props.onChange(newValue, "effect");
    }
}
