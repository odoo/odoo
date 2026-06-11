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
    constructor(options = {}) {
        options.tag = "IMG";
        super(options);
        this.setAttributes({
            classNames: "o-ci-image",
        });
    }
}
