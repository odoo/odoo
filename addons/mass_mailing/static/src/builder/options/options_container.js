import { OptionsContainer } from "@html_builder/sidebar/option_container";
import { useState } from "@odoo/owl";

export class OptionsContainerWithSnippetVersionControl extends OptionsContainer {
    static template = "mass_mailing.OptionsContainer";
    setup() {
        super.setup();
        this.versionState = useState({
            isUpToDate: this.env.editor.shared.versionControl.hasAccessToOutdatedEl(
                this.props.editingElement
            ),
        });
    }
    // Version control
    replaceElementWithNewVersion() {
        this.callOperation(() => {
            this.env.editor.shared.versionControl.replaceWithNewVersion(this.props.editingElement);
        });
    }
    accessOutdated() {
        this.env.editor.shared.versionControl.giveAccessToOutdatedEl(this.props.editingElement);
        this.versionState.isUpToDate = true;
    }
}
