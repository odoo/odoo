import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class ImageAndFaOption extends BaseOptionComponent {
    static template = "html_builder.ImageAndFaOption";

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            isIcon: editingElement.matches("span.fa, i.fa"),
        }));
    }
}
