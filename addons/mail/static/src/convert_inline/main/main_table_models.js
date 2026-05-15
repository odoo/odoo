import { assignDefaultElementOptions, LayoutModel } from "../core/render_models";

/**
 * TODO EGGMAIL: evaluate if the browser does add `<tbody>` element to the final
 * render, if yes, identify where:
 * is it when inserted in the DOM/in the fragment/in the template
 */
export class MainTable extends LayoutModel {
    static template = "mail.MainTable";
    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
        refs.td = assignDefaultElementOptions(refs.td, {
            style: {
                padding: "0",
            },
        });
        super(options);
        this.setAttributes({
            style: {
                border: "0",
                "border-spacing": "0",
                width: "100%",
            },
            attributes: {
                align: "center",
                role: "presentation",
            },
        });
    }

    get ancestorTag() {
        return "TABLE";
    }

    get descendantTag() {
        return "TD";
    }
}

export class MainTableLayout extends MainTable {
    constructor(options = {}) {
        super(options);
        this.setAttributes({
            classNames: "o-ci-layout",
        });
    }
}

export class MainTableWrapper extends MainTable {
    constructor(options = {}) {
        super(options);
        this.setAttributes({
            classNames: "o-ci-mail-wrapper",
        });
    }
}
