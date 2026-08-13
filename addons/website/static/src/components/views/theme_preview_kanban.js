/** @odoo-module */

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useLoaderOnClick } from './theme_preview_form';
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

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
    static template = "website.ThemePreviewKanban.ControlPanel";
    setup() {
        super.setup();
        this.website = useService('website');
    }
    close() {
        this.website.goToWebsite();
    }

    get display() {
        return {
            layoutActions: false,
            ...this.props.display,
        };
    }
}
class ThemePreviewKanbanrecord extends KanbanRecord {

    /** @override **/
    getRecordClasses() {
        return super.getRecordClasses() + " p-0 border-0 bg-transparent";
    }
}

export class ThemePreviewKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: ThemePreviewKanbanrecord,
    };
}

const ThemePreviewKanbanView = {
    ...kanbanView,
    Controller: ThemePreviewKanbanController,
    ControlPanel: ThemePreviewControlPanel,
    Renderer: ThemePreviewKanbanRenderer,
    display: {
        controlPanel: {},
    },
};



registry.category('views').add('theme_preview_kanban', ThemePreviewKanbanView);
