import { ElementLayout, LayoutModel } from "../core/render_models";

export class ImageLinkLayout extends LayoutModel {
    static template = "mail.ImageLink";

    constructor(options = {}) {
        super(options);
        this.setAttributes({
            classNames: "o-ci-image-link",
        });
    }

    get ancestorTag() {
        return "A";
    }

    get descendantTag() {
        return "IMG";
    }
}

export class ImageLayout extends ElementLayout {
    constructor(root = {}) {
        root.tag = "IMG";
        super(root);
        this.setAttributes({
            classNames: "o-ci-image",
        });
    }
}
