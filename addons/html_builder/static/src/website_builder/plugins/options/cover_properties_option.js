import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class CoverPropertiesOption extends BaseOptionComponent {
    static template = "html_builder.CoverPropertiesOption";
    static props = {};

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            useTextAlign: editingElement.dataset.use_text_align === "True",
            useSize: editingElement.dataset.use_size === "True",
        }));
    }
}
