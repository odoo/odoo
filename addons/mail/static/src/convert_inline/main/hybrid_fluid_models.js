import { assignDefaultElementOptions, ElementLayout, LayoutModel } from "../core/render_models";

export class HybridFluidRow extends ElementLayout {
    constructor(options = {}) {
        const root = assignDefaultElementOptions(options, {
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
    constructor(options = {}) {
        const root = assignDefaultElementOptions(options, {
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
