import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { FontFamilyPicker } from "../fontfamily_picker";
import { BaseOptionComponent } from "@html_builder/core/utils";

export const OPTION_POSITIONS = {
    BODY: 10,
    SETTINGS: 20,
    HEADINGS: 30,
    PARAGRAPH: 40,
    BUTTON: 50,
    LINK: 60,
    SEPARATORS: 70,
};

class DesignTabPlugin extends Plugin {
    static id = "mass_mailing.DesignTab";
    static dependencies = ["builderActions"];
    resources = {
        builder_components: {
            FontFamilyPicker,
        },
        design_options: [
            withSequence(
                OPTION_POSITIONS.BODY,
                this.getDesignOptionBlock("design-body", {
                    template: "mass_mailing.DesignBodyOption",
                    title: _t("Body"),
                })
            ),
            withSequence(
                OPTION_POSITIONS.HEADINGS,
                this.getDesignOptionBlock("design-headings", {
                    template: "mass_mailing.DesignHeadingsOption",
                    title: _t("Heading"),
                })
            ),
            withSequence(
                OPTION_POSITIONS.PARAGRAPH,
                this.getDesignOptionBlock("design-paragraph", {
                    template: "mass_mailing.DesignParagraphOption",
                    title: _t("Paragraph"),
                })
            ),
            withSequence(
                OPTION_POSITIONS.BUTTON,
                this.getDesignOptionBlock("design-button", {
                    template: "mass_mailing.DesignButtonOption",
                    title: _t("Button"),
                })
            ),
            withSequence(
                OPTION_POSITIONS.LINK,
                this.getDesignOptionBlock("design-link", {
                    template: "mass_mailing.DesignLinkOption",
                    title: _t("Link"),
                })
            ),
            withSequence(
                OPTION_POSITIONS.SEPARATORS,
                this.getDesignOptionBlock("design-separators", {
                    template: "mass_mailing.DesignSeparatorOption",
                    title: _t("Separator"),
                })
            ),
        ],
    };

    getDesignOptionBlock(id, options) {
        const Option = class extends BaseOptionComponent {
            static selector = "*";
        };
        Object.assign(Option, options);

        return {
            id: id,
            element: this.editable,
            hasOverlayOptions: false,
            headerMiddleButton: false,
            isClonable: false,
            isRemovable: false,
            options: [Option],
            optionsContainerTopButtons: [],
            snippetModel: {},
        };
    }
}

registry.category("mass_mailing-plugins").add(DesignTabPlugin.id, DesignTabPlugin);
