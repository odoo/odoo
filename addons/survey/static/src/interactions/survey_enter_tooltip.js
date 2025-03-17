import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { isMacOS } from "@web/core/browser/feature_detection";

class SurveyEnterTooltip extends Interaction {
    static selector = ".o_survey_form #enter-tooltip";

    dynamicSelectors = {
        ...this.dynamicSelectors,
        _inputs: () => document.querySelectorAll(".o_survey_form .form-control"),
    };

    dynamicContent = {
        _inputs: {
            "t-on-focusin": this.updateEnterButtonText,
            "t-on-focusout": this.updateEnterButtonText,
        },
        _root: {
            "t-out": () => this.enterTooltipText,
        },
    };

    setup() {
        this.isMac = isMacOS();
        this.enterTooltipText = this.el.textContent;
        this.options = this.services.survey.options;
    }

    start() {
        const activeEl = document.activeElement;
        this.updateTooltip(
            document.hasFocus() &&
                activeEl.tagName.toLowerCase() === "textarea" &&
                activeEl.classList.contains("form-control")
        );
        this.updateContent();
    }

    updateEnterButtonText(event) {
        const targetEl = event.target;
        const isTextbox = event.type === "focusin" && targetEl.tagName.toLowerCase() === "textarea";
        this.updateTooltip(isTextbox);
    }

    updateTooltip(isTextbox) {
        this.enterTooltipText = _t("or press Enter");
        if (["one_page", "page_per_section"].includes(this.options.questionsLayout) || isTextbox) {
            this.enterTooltipText = this.isMac ? _t("or press ⌘+Enter") : _t("or press CTRL+Enter");
        }
    }
}

registry.category("public.interactions").add("survey.SurveyEnterTooltip", SurveyEnterTooltip);
