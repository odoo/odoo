import { ElementLayout, LayoutModel } from "../core/render_models";

export class TableLayout extends ElementLayout {
    constructor(root = {}) {
        root.tag = "TABLE";
        super(root);
        this.setAttributes({
            classNames: "o-ci-table-layout",
            attributes: {
                role: "presentation",
                cellspacing: "0",
                cellpadding: "0",
                border: "0",
            },
        });
    }
}

export class RowLayout extends ElementLayout {
    constructor(root = {}) {
        root.tag = "TR";
        super(root);
        this.setAttributes({
            classNames: "o-ci-row-layout",
        });
    }
}

export class EmptyRowLayout extends LayoutModel {
    static template = "mail.EmptyRowLayout";
    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
        super(options);
        this.setAttributes({ classNames: "o-ci-empty-row-cell" }, "cell");
    }

    get ancestorTag() {
        return "TR";
    }

    get descendantTag() {
        return "TD";
    }
}

export class CellLayout extends ElementLayout {
    constructor(root = {}) {
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
}
