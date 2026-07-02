import { assignDefaultElementOptions, ElementLayout, LayoutModel } from "../core/render_models";

export class TableRowLayout extends LayoutModel {
    static template = "mail.TableRow";
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
            classNames: "o-ci-table-layout",
            style: {
                "border-collapse": "separate",
            },
        });
        this.setAttributes(
            {
                classNames: "o-ci-row-layout",
            },
            "row"
        );
    }

    get ancestorTag() {
        return "TABLE";
    }

    get descendantTag() {
        return "TR";
    }
}

export class CellLayout extends ElementLayout {
    constructor(root = {}) {
        root = assignDefaultElementOptions(root, {
            attributes: {
                valign: "top",
            },
            style: {
                "vertical-align": "top",
            },
        });
        root.tag = "TD";
        super(root);
        this.setAttributes({
            classNames: "o-ci-cell-layout",
        });
    }
}

export class EmptyCellLayout extends CellLayout {
    constructor(root = {}) {
        super(root);
        this.setAttributes({
            style: { height: 0 },
            attributes: { height: 0 },
        });
    }

    renderToFragment(context = {}) {
        const fragment = super.renderToFragment(context);
        const comment = document.createComment("");
        // TODO EGGMAIL: is there a better solution?
        // body_html is normalized as xml, and empty elements in xml are
        // self closing. This is not legal in html, so an empty comment is
        // appended to avoid the issue.
        fragment.firstElementChild.append(comment);
        return fragment;
    }
}
