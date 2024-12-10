import { ControlPanel } from "@web/search/control_panel/control_panel";


export class ProjectSharingControlPanel extends ControlPanel {
    setup() {
        super.setup();
        this.breadcrumbs.unshift({
            name: 'Project',
            url: '/my/projects',
            onSelected: () => {
                window.top.location.href = '/my/projects';
            },
        });
    }
}
