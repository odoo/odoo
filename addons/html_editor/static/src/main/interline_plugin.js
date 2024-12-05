import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

export class InterlinePlugin extends Plugin {
    static name = "interline";
    static dependencies = ["dom", "baseContainer"];
    resources = {
        user_commands: [
            {
                id: "setTagParagraph",
                title: _t("Text"),
                description: _t("Paragraph block"),
                icon: "fa-paragraph",
                run: () => {
                    this.dependencies.baseContainer.setBaseContainer("P");
                    const baseContainer = this.dependencies.baseContainer.getBaseContainer();
                    this.dependencies.dom.setTag({
                        tagName: baseContainer.nodeName,
                        identityClasses: [...baseContainer.classSet],
                    });
                },
            },
            {
                id: "setTagParagraph",
                title: _t("Text without interline"),
                description: _t("Paragraph block without interline"),
                icon: "fa-paragraph",
                run: () => {
                    this.dependencies.baseContainer.setBaseContainer("DIV");
                    const baseContainer = this.dependencies.baseContainer.getBaseContainer();
                    this.dependencies.dom.setTag({
                        tagName: baseContainer.nodeName,
                        identityClasses: [...baseContainer.classSet],
                    });
                },
            },
        ],
        powerbox_categories: withSequence(30, { id: "format", name: _t("Format") }),
        powerbox_items: [
            {
                categoryId: "format",
                commandId: "setTagParagraph",
            },
            {
                categoryId: "format",
                commandId: "setTagNoInterlineParagraph",
            },
        ],
    };
}
