/** @odoo-module */

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useLoaderOnClick } from './theme_preview_form';

class ThemePreviewKanbanController extends KanbanController {
    /**
     * @override
     */
    setup() {
        super.setup();
        useLoaderOnClick();
    }
}

class ThemePreviewControlPanel extends ControlPanel {
    setup() {
        super.setup();
        this.website = useService('website');
    }
    close() {
        this.website.goToWebsite();
    }
}
ThemePreviewControlPanel.template = 'website.ThemePreviewKanban.ControlPanel';

const ThemePreviewKanbanView = {
    ...kanbanView,
    Controller: ThemePreviewKanbanController,
    ControlPanel: ThemePreviewControlPanel,
    display: {
        controlPanel: {
            'bottom-left': false,
            'bottom-right': false,
        },
    },
};



registry.category('views').add('theme_preview_kanban', ThemePreviewKanbanView);
