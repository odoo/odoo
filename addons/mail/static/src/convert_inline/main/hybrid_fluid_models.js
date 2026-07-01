import { assignDefaultElementOptions, ElementLayout, LayoutModel } from "../core/render_models";

export class HybridFluidRow extends ElementLayout {
    constructor(root = {}) {
        root = assignDefaultElementOptions(root, {
            // TODO EGGMAIL: RTL check
            style: {
                "text-align": "center",
            },
        });
        super(root);
        this.setAttributes({
            classNames: "o-ci-hybrid-fluid-row",
            style: {
                "font-size": "0",
            },
        });
    }
}

export class HybridFluidCellWithOffset extends ElementLayout {
    constructor(root = {}) {
        root = assignDefaultElementOptions(root, {
            style: {
                "max-width": "100%",
                "vertical-align": "top",
            },
        });
        super(root);
        this.setAttributes({
            classNames: "o-ci-hybrid-fluid-cell-with-offset",
            style: {
                display: "inline-block",
                width: "100%",
            },
        });
    }
}

export class HybridFluidCell extends LayoutModel {
    static template = "mail.HybridFluidCell";
    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
        refs.root = assignDefaultElementOptions(refs.root, {
            style: {
                "max-width": "100%",
                "vertical-align": "top",
            },
        });
        refs.styleContext = assignDefaultElementOptions(refs.styleContext, {
            // TODO EGGMAIL: RTL check
            style: {
                "text-align": "left",
                "font-size": "14px",
            },
        });
        super(options);
        this.setAttributes({
            classNames: "o-ci-hybrid-fluid-cell",
            style: {
                display: "inline-block",
                width: "100%",
            },
        });
    }

    get ancestorTag() {
        return "DIV";
    }

    get descendantTag() {
        return "DIV";
    }
}

export class HybridFluidEmptyCell extends HybridFluidCell {
    static template = "mail.ElementLayout";
    constructor() {
        super(...arguments);
        this.tag = "DIV";
        this.setAttributes({
            style: {
                height: 0,
            },
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

export class HybridFluidTableRow extends LayoutModel {
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
            classNames: "o-ci-hybrid-fluid-table",
            style: {
                "border-collapse": "separate",
            },
        });
        this.setAttributes(
            {
                classNames: "o-ci-hybrid-fluid-table-row",
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

export class HybridFluidTableCell extends ElementLayout {
    constructor(root = {}) {
        root.tag = "TD";
        super(root);
        this.setAttributes({
            classNames: "o-ci-hybrid-fluid-table-cell",
            attributes: {
                valign: "top",
            },
            style: {
                "vertical-align": "top",
            },
        });
    }
}
