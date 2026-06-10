import { ElementLayout } from "../core/render_models";

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

export class CellLayout extends ElementLayout {
    constructor(root = {}) {
        root.tag = "TD";
        super(root);
        this.setAttributes({
            classNames: "o-ci-cell-layout",
        });
    }
}
