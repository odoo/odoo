import { assignDefaultElementOptions, ElementLayout, LayoutModel } from "../core/render_models";

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
    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
        refs.root ??= {};
        refs.root.tag = "TD";
        refs.root = assignDefaultElementOptions(refs.root, {
            attributes: {
                valign: "top",
            },
            style: {
                // TODO EGGMAIL: there are some configurations where we would
                // want this to be "middle" by default (eg in a header)
                "vertical-align": "top",
            },
        });
        super(options);
        this.setAttributes({
            classNames: "o-ci-hybrid-fluid-table-cell",
        });
    }
}
