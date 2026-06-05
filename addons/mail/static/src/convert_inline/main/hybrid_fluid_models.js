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
    constructor() {
        super(...arguments);
        this.setAttributes({
            style: {
                height: 0,
            },
        });
    }

    get isEmpty() {
        return true;
    }
}

export class HybridFluidTableRow extends LayoutModel {
    static template = "mail.HybridFluidTableRow";
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
        });
        this.setAttributes({
            classNames: "o-ci-hybrid-fluid-table-row",
        });
    }
}

export class HybridFluidTableCell extends ElementLayout {
    constructor(root = {}) {
        root.tag = "TD";
        super(root);
        this.setAttributes({
            classNames: "o-ci-hybrid-fluid-table-cell",
        });
    }
}

export class HybridFluidEmptyTableCell extends HybridFluidTableCell {
    constructor(root = {}) {
        super(root);
        this.setAttributes({
            style: { height: 0 },
        });
    }
}
