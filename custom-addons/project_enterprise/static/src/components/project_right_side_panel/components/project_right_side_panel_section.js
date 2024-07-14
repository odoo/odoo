/** @odoo-module */

import { useBus, useService } from '@web/core/utils/hooks';
import { patch } from "@web/core/utils/patch";
import { ProjectRightSidePanelSection } from '@project/components/project_right_side_panel/components/project_right_side_panel_section';
import { useState } from "@odoo/owl";

patch(ProjectRightSidePanelSection.prototype, {
    setup() {
        this.state = useState({ isClosed: !!this.env.isSmall && this.props.canBeClosed });
        this.ui = useService('ui');

        useBus(this.ui.bus, "resize", this.setDefaultIsClosed);
    },

    setDefaultIsClosed() {
        this.state.isClosed = this.ui.isSmall && this.props.canBeClosed;
    },

    toggleSection() {
        if (!this.env.isSmall || !this.props.canBeClosed) { // then no need to change the value.
            this.state.isClosed = false;
        } else {
            this.state.isClosed = !this.state.isClosed;
        }
    }
});

ProjectRightSidePanelSection.props.canBeClosed = { type: Boolean, optional: true };
ProjectRightSidePanelSection.defaultProps.canBeClosed = true;
