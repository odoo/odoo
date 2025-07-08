import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const OPTION_POSITIONS = {
    BODY: 10,
    SETTINGS: 20,
    HEADINGS: 30,
    PARAGRAPH: 40,
    BUTTON: 50,
    LINK: 60,
};

// TODO EGGMAIL: ensure that there is a .o_layout and a .container element
// in the DOM, always. Reset from known theme if needed, wrap current content
// in theme_wrapper? Investigate.
class DesignTabPlugin extends Plugin {
    static id = "mass_mailing.DesignTab";
    static dependencies = ["builderActions"];
    resources = {
        design_options: [
            withSequence(
                OPTION_POSITIONS.BODY,
                this.getDesignOptionBlock("design-body", _t("Body"), {
                    template: "mass_mailing_egg.DesignBodyOption",
                })
            ),
            withSequence(
                OPTION_POSITIONS.HEADINGS,
                this.getDesignOptionBlock("design-headings", _t("Headings"), {
                    template: "mass_mailing_egg.DesignHeadingsOption",
                })
            ),
            withSequence(
                OPTION_POSITIONS.PARAGRAPH,
                this.getDesignOptionBlock("design-paragraph", _t("Paragraph"), {
                    template: "mass_mailing_egg.DesignParagraphOption",
                })
            ),
            withSequence(
                OPTION_POSITIONS.BUTTON,
                this.getDesignOptionBlock("design-button", _t("Button"), {
                    template: "mass_mailing_egg.DesignButtonOption",
                })
            ),
            withSequence(
                OPTION_POSITIONS.LINK,
                this.getDesignOptionBlock("design-link", _t("Link"), {
                    template: "mass_mailing_egg.DesignLinkOption",
                })
            ),
        ],
    };

    getDesignOptionBlock(id, name, options) {
        const el = this.document.createElement("div");
        el.dataset.name = name;
        this.document.body.appendChild(el); // Currently editingElement needs to be isConnected

        options.selector = "*";

        return {
            id: id,
            element: el,
            hasOverlayOptions: false,
            headerMiddleButton: false,
            isClonable: false,
            isRemovable: false,
            options: [options],
            optionsContainerTopButtons: [],
            snippetModel: {},
        };
    }
}

registry.category("mass_mailing-plugins").add(DesignTabPlugin.id, DesignTabPlugin);
