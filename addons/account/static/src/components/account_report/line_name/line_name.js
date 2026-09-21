/** @odoo-module native */
import { parseLineId } from "@account/js/util";
import { Component, useRef, useState } from "@odoo/owl";
import { Dropdown, DropdownItem } from "@web/components/dropdown";
import { useService } from "@web/core/utils/hooks";

export class AccountReportLineName extends Component {
    static template = "account.AccountReportLineName";
    static props = {
        lineIndex: Number,
        line: Object,
    };
    static components = {
        Dropdown,
        DropdownItem,
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.ui = useService("ui");
        this.controller = useState(this.env.controller);

        this.lineNameCell = useRef("lineNameCell");
    }

    get modelName() {
        return parseLineId(this.props.line.id).at(-1)[1];
    }

    //------------------------------------------------------------------------------------------------------------------
    // Caret options
    //------------------------------------------------------------------------------------------------------------------
    get caretOptions() {
        return this.controller.caretOptions[this.props.line.caret_options];
    }

    get hasCaretOptions() {
        return this.caretOptions?.length > 0;
    }

    async caretAction(caretOption) {
        const res = await this.orm.call(
            "account.report",
            "dispatch_report_action",
            [
                this.controller.options.report_id,
                this.controller.options,
                caretOption.action,
                {
                    line_id: this.props.line.id,
                    action_param: caretOption.action_param,
                },
            ],
            {
                context: this.controller.context,
            },
        );

        return this.action.doAction(res);
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Classes
    // -----------------------------------------------------------------------------------------------------------------
    get lineNameClasses() {
        let classes = "text";

        if (this.props.line.unfoldable) {
            classes += " unfoldable";
        }

        if (this.props.line.is_draft) {
            classes += " draft";
        }

        if (this.props.line.class) {
            classes += ` ${this.props.line.class}`;
        }

        return classes;
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Action
    // -----------------------------------------------------------------------------------------------------------------
    async triggerAction() {
        const res = await this.orm.call(
            "account.report",
            "execute_action",
            [
                this.controller.options.report_id,
                this.controller.options,
                {
                    id: this.props.line.id,
                    actionId: this.props.line.action_id,
                },
            ],
            {
                context: this.controller.context,
            },
        );

        return this.action.doAction(res);
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Load more
    // -----------------------------------------------------------------------------------------------------------------
    async loadMore() {
        const newLines = await this.orm.call("account.report", "get_expanded_lines", [
            this.controller.options.report_id,
            this.controller.options,
            this.props.line.parent_id,
            this.props.line.groupby,
            this.props.line.expand_function,
            this.props.line.progress,
            this.props.line.offset,
            this.props.line.horizontal_split_side,
        ]);

        this.controller.setLineVisibility(newLines);
        if (this.controller.areLinesOrdered()) {
            this.controller.updateLinesOrderIndexes(
                this.props.lineIndex,
                newLines,
                true,
            );
        }
        await this.controller.replaceLineWith(this.props.lineIndex, newLines);
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Fold / Unfold
    // -----------------------------------------------------------------------------------------------------------------
    toggleFoldable() {
        if (this.props.line.unfoldable) {
            if (this.props.line.unfolded) {
                this.controller.foldLine(this.props.lineIndex);
            } else {
                this.controller.unfoldLine(this.props.lineIndex);
            }
        }
    }
}
