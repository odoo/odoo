import { TemplateLayout } from "@mail/convert_inline/core/render_models";

export class MainTable extends TemplateLayout {
    static template = "mail.MainTable";
    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
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
