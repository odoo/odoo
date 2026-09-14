/** @odoo-module native */
import { Component, useEffect, useState } from "@odoo/owl";
import { Dropdown, DropdownItem } from "@web/components/dropdown";
import { useService } from "@web/core/utils/hooks";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { SIZES } from "@web/ui/viewport";

export class DocumentsAction extends Component {
    static template = "document.DocumentsAction";
    static components = {
        ActionMenus,
        Dropdown,
        DropdownItem,
    };
    static props = {
        targetRecords: Array,
        folderId: [String, Number, Boolean],
        isPreview: { type: Boolean, optional: true },
    };

    setup() {
        this.documentService = useService("document.document");
        this.state = useState({
            topbarActions: [],
            actionMenuProps: null,
        });
        this.ui = useState(useService("ui"));
        this.selectionActions = useState(this.documentService.selectionActions);
        useEffect(
            () => {
                if (this.selectionActions.provider) {
                    const selectionActions = this.selectionActions.provider();
                    this.state.topbarActions = Object.values(
                        selectionActions.getTopbarActions(),
                    ).sort((a, b) => a.groupNumber - b.groupNumber);
                    if (this.props.isPreview) {
                        const actionMenuProps = selectionActions.getMenuProps();
                        actionMenuProps.items.action =
                            actionMenuProps.items.action.filter(this.isPreviewAction);
                        this.state.actionMenuProps = actionMenuProps;
                    }
                }
            },
            () => [
                this.props.targetRecords,
                this.ui.isSmall,
                this.selectionActions.provider,
            ],
        );
    }

    get topbarActions() {
        return this.state.topbarActions.filter(
            (action) => !action.isAvailable || action.isAvailable(),
        );
    }

    get visibleTopbarActions() {
        return this.ui.size >= SIZES.XL ? 3 : 2;
    }

    isPreviewAction(action) {
        return action.key !== "export";
    }
}
