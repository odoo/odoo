import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { KeepLast } from "@web/core/utils/concurrency";
import { getImageSrc, getMimetype } from "@html_editor/utils/image";

export class ImageFormatOption extends BaseOptionComponent {
    static template = "website.ImageFormat";
    static props = {
        level: { type: Number, optional: true },
        computeFrom: {
            type: String,
            validate: (val) => ["background", "image"].includes(val),
            optional: true,
        },
    };
    static defaultProps = {
        level: 0,
        computeFrom: "image",
    };
    setup() {
        super.setup();
        const keepLast = new KeepLast();
        this.state = useDomState((editingElement) => {
            keepLast
                .add(
                    this.env.editor.shared.imageFormatOption.computeAvailableFormats(
                        editingElement,
                        this.props.computeFrom
                    )
                )
                .then((formats) => {
                    const hasSrc = !!getImageSrc(editingElement);
                    this.state.formats = hasSrc ? formats : [];
                });
            return {
                showQuality: ["image/jpeg", "image/webp"].includes(getMimetype(editingElement)),
                formats: [],
            };
        });
    }
}
