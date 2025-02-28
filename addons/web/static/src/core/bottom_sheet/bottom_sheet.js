import { Component, useChildSubEnv, useState } from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";
import { useActiveElement } from "../ui/ui_service";

/**
 * BottomSheet
 *
 * This component focuses on the content of the sheet.
 * The container, positioning, and scroll behavior are handled by BottomSheetContainer.
 */
export class BottomSheet extends Component {
    static template = "web.BottomSheet";
    static props = {
        bodyClass: { type: String, optional: true },
        footer: { type: Boolean, optional: true },
        header: { type: Boolean, optional: true },
        showCloseBtn: { type: Boolean, optional: true },
        showBackBtn: { type: Boolean, optional: true },
        title: { type: String, optional: true },
        bottomSheetRootRef: { type: Function, optional: true },
        forceExtendedFullHeight: { type: Boolean, optional: true },
        visibleInitialMax: { type: Number, optional: true },
        visibleExtended: { type: Number, optional: true },

        slots: {
            type: Object,
            shape: {
                default: Object,
                header: { type: Object, optional: true },
                footer: { type: Object, optional: true },
            },
        },
        withBodyPadding: { type: Boolean, optional: true },
        close: { type: Function, optional: true },
    };

    static defaultProps = {
        withBodyPadding: true,
        visibleInitialMax: 40,
        visibleExtended: 90,
        forceExtendedFullHeight: false,
    };

    setup() {
        this.bottomSheetRootRef = useForwardRefToParent("bottomSheetRootRef");
        useActiveElement("bottomSheetRootRef");

        // Get data from environment if provided by service
        this.data = useState(this.env.bottomSheetData || {
            id: 0,
            isActive: true,
            close: this.props.close || (() => {}),
        });

        this.id = `o_bottom_sheet_${this.data.id}`;
        useChildSubEnv({ inBottomSheet: true, bottomSheetId: this.id });
    }

    /**
     * Close the sheet
     */
    dismiss() {
        if (this.data.close) {
            this.data.close();
        } else if (this.props.close) {
            this.props.close();
        }
    }
}