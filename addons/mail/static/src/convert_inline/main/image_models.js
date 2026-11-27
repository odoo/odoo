import {
    assignDefaultElementOptions,
    ElementLayout,
    TemplateLayout,
} from "@mail/convert_inline/core/render_models";

export class ImageLinkLayout extends TemplateLayout {
    static template = "mail.ImageLink";

    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
        refs.root = assignDefaultElementOptions(refs.root, {
            style: { "text-decoration": { value: "none", priority: "important" } },
        });
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
        const refs = options.refs ?? {};
        options.refs = refs;
        refs.root ??= {};
        refs.root.tag = "IMG";
        super(options);
        this.setAttributes({
            classNames: "o-ci-image",
        });
    }
}
