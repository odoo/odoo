/** @odoo-module */

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { Component, useState, useRef } from "@odoo/owl";

import { AccountReportAnnotationsPopover } from "@account_reports/components/account_report/line_name/popover/annotations_popover";

export class AccountReportLineName extends Component {
    static template = "account_reports.AccountReportLineName";
    static props = {
        lineIndex: Number,
        line: Object,
    };
    static components = {
        Dropdown,
        DropdownItem,
    }

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.controller = useState(this.env.controller);
        this.annotationPopOver = usePopover(AccountReportAnnotationsPopover, {
            setActiveElement: false,
            position: "bottom",
            animation: false,
            closeOnClickAway: (target) => !target.closest(".annotation_popover"),
        });

        this.lineNameCell = useRef("lineNameCell");
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
            }
        );

        return this.action.doAction(res);
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Classes
    // -----------------------------------------------------------------------------------------------------------------
    get lineNameClasses() {
        let classes = "text";

        if (this.props.line.unfoldable)
            classes += " unfoldable";

        if (this.props.line.class)
            classes += ` ${ this.props.line.class }`;

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
            }
        );

        return this.action.doAction(res);
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Load more
    // -----------------------------------------------------------------------------------------------------------------
    async loadMore() {
        const newLines = await this.orm.call(
            "account.report",
            "get_expanded_lines",
            [
                this.controller.options.report_id,
                this.controller.options,
                this.props.line.parent_id,
                this.props.line.groupby,
                this.props.line.expand_function,
                this.props.line.progress,
                this.props.line.offset,
                this.props.line.horizontal_split_side,
            ],
        );

        this.controller.setLineVisibility(newLines)
        if (this.controller.areLinesOrdered()) {
            this.controller.updateLinesOrderIndexes(this.props.lineIndex, newLines, true)
        }
        await this.controller.replaceLineWith(this.props.lineIndex, newLines);
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Fold / Unfold
    // -----------------------------------------------------------------------------------------------------------------
    toggleFoldable() {
        if (this.props.line.unfoldable)
            if (this.props.line.unfolded)
                this.controller.foldLine(this.props.lineIndex);
            else
                this.controller.unfoldLine(this.props.lineIndex);
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Annotation
    // -----------------------------------------------------------------------------------------------------------------
    get hasVisibleAnnotation() {
        return this.props.line.visible_annotations;
    }

    //------------------------------------------------------------------------------------------------------------------
    // Annotation Popover
    //------------------------------------------------------------------------------------------------------------------
    async toggleAnnotationPopover() {
        if (this.annotationPopOver.isOpen) {
            this.annotationPopOver.close();
        } else {
            this.annotationPopOver.open(this.lineNameCell.el, {
                controller: this.controller,
                lineName: this,
                lineID: this.props.line.id,
            });
        }
    }

    async addAnnotation(ev) {
        this.annotationPopOver.open(this.lineNameCell.el, {
            controller: this.controller,
            lineName: this,
            isAddingAnnotation: true,
            lineID: this.props.line.id,
        });
    }
}
