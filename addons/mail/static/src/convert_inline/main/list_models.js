import { assignDefaultElementOptions, LayoutModel } from "../core/render_models";

export class FakeListContainer extends LayoutModel {
    static template = "mail.FakeListContainer";
    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
        refs.table ??= {};
        refs.table = assignDefaultElementOptions(refs.table, {
            style: {
                width: "100%",
            },
        });
        super(options);
        this.setAttributes(
            {
                style: {
                    "border-collapse": "separate",
                },
                classNames: "o-ci-table-list",
            },
            "table"
        );
    }

    get ancestorTag() {
        return "DIV";
    }

    get descendantTag() {
        return "TABLE";
    }
}

export class FakeListItem extends LayoutModel {
    static template = "mail.FakeListItem";
    constructor(options = {}) {
        super(options);
        this.setAttributes(
            {
                classNames: "o-ci-cell-list-item",
            },
            "cell"
        );
    }

    get ancestorTag() {
        return "TR";
    }

    get descendantTag() {
        return "DIV";
    }
}
