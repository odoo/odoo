import { LinkPopover } from "@html_editor/main/link/link_popover";
import { useState } from "@odoo/owl";

export class WebsiteLinkPopover extends LinkPopover {
    static template = "website.websiteLinkPopover";

    setup() {
        super.setup();
        const currentRelValues = this.props.linkElement.rel.split(" ");
        const relAttributeOptions = Object.fromEntries(
            this.props.relAttributeOptions.map((option) => [
                option.label,
                { ...option, isChecked: currentRelValues.includes(option.label) },
            ])
        );
        this.linkstate = useState({
            linkTarget: this.props.linkElement.target === "_blank" ? "_blank" : "",
            showAdvancedOptions: false,
            relAttributeOptions: relAttributeOptions,
        });
    }

    toggleAdvancedOptions() {
        this.linkstate.showAdvancedOptions = !this.linkstate.showAdvancedOptions;
    }

    toggleRelAttr(attr) {
        const option = this.linkstate.relAttributeOptions[attr];
        option.isChecked = !option.isChecked;
    }

    onClickNewWindow(checked) {
        this.linkstate.linkTarget = checked ? "_blank" : "";
        if (!checked) {
            this.linkstate.relAttributeOptions.noopener.isChecked = false;
        }
    }

    prepareParams() {
        const relOptions = this.linkstate.relAttributeOptions;
        const relValue = Object.keys(relOptions)
            .filter((key) => relOptions[key].isChecked)
            .join(" ");
        return {
            ...super.prepareParams(),
            linkTarget: this.linkstate.linkTarget,
            relValue: relValue,
        };
    }
}
