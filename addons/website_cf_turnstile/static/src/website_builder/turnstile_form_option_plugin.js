import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { FormOptionPlugin } from "@website/builder/plugins/form/form_option_plugin";

export class TurnstileFormOptionPlugin extends Plugin {
    static id = "turnstileFormOption";
    static dependencies = ["websiteBridge"];
    static shared = ["hasTurnstileKey"];
    resources = {
        builder_actions: {
            FormToggleTurnstileLegalAction,
        },
        content_editable_selectors: ".s_website_form form .s_website_form_turnstile",
    };

    hasTurnstileKey() {
        return !!this.dependencies.websiteBridge.getSession().turnstile_site_key;
    }
}

export class FormToggleTurnstileLegalAction extends BuilderAction {
    static id = "formToggleTurnstileLegal";
    static dependencies = ["websiteBridge"];
    apply({ editingElement: el }) {
        const legalEl = this.dependencies.websiteBridge.renderToElement(
            "website_cf_turnstile.s_website_form_turnstile_legal"
        );
        legalEl.setAttribute("contentEditable", true);
        el.querySelector(".s_website_form_submit").insertAdjacentElement("beforebegin", legalEl);
    }
    clean({ editingElement: el }) {
        el.querySelector(".s_website_form_turnstile").remove();
    }
    isApplied({ editingElement: el }) {
        return !!el.querySelector(".s_website_form_turnstile");
    }
}

function moveTurnstileBeforeSubmit(formEl) {
    const turnstileEl = formEl.querySelector(".s_website_form_turnstile");
    const submitEl = formEl.querySelector(".s_website_form_submit");
    if (turnstileEl && submitEl) {
        submitEl.insertAdjacentElement("beforebegin", turnstileEl);
    }
}

patch(FormOptionPlugin.prototype, {
    async applyFormModel(el) {
        const result = await super.applyFormModel(...arguments);
        moveTurnstileBeforeSubmit(el);
        return result;
    },
    addField(editingElement) {
        super.addField(...arguments);
        const formEl = editingElement.closest("form");
        if (formEl) {
            moveTurnstileBeforeSubmit(formEl);
        }
    },
});

registry.category("website-plugins").add(TurnstileFormOptionPlugin.id, TurnstileFormOptionPlugin);
