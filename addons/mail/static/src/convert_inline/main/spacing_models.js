import { assignDefaultElementOptions, LayoutModel } from "../core/render_models";

export class SpacingLayout extends LayoutModel {
    static template = "mail.SpacingLayout";

    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
        refs.root = assignDefaultElementOptions(refs.root, {
            style: {
                width: "100%",
            },
        });
        super(options);
        this.setAttributes({
            classNames: "o-ci-spacing-wrapper",
        });
    }

    get ancestorTag() {
        return "TABLE";
    }

    get descendantTag() {
        return "TD";
    }
}

/**
 * Wrapper for a spacing layout, compatible with EmailNode render function.
 */
export class SpacingNode {
    constructor({ Layout = SpacingLayout, refs = {} } = {}) {
        this.layout = new Layout({ refs });
    }
}
