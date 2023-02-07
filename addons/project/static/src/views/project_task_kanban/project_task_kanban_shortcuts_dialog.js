/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { _lt } from '@web/core/l10n/translation';
import { session } from "@web/session";

const { Component, onMounted } = owl;

export class ProjectTaskKanbanShortcutsDialog extends Component {
    setup() {
        super.setup();
        this.tips = {
            title: 'Shortcuts to create tasks',
            subtitle: 'Use these keywords in the title to set new tasks',
            attributes: [
                {
                    key: '+tags',
                    value: 'Set tags on the task',
                },
                {
                    key: 'title !',
                    value: 'Put task in priority',
                },
                {
                    key: '@me',
                    value: 'Assign the task to me',
                },
            ],
            example: {
                formFields: [
                    {
                        key: 'Task Title',
                        value: 'Improve configuration screen @me +feature +v16 !',
                    },
                ],
                buttons: [
                    'Add',
                ],
                box: {
                    title: 'Improve configuration screen',
                    assigned_to_me: true,
                    tags: [
                        {
                            name: 'feature',
                            bulletColor: '--c: orange',
                        },
                        {
                            name: 'v16',
                            bulletColor: '--c: red',
                        },
                    ],
                    high_priority: true,
                }
            }
        };
        onMounted(() => {
            document.getElementById("avatar").src = `/web/image/res.users/${session.uid}/avatar_128`;
        });
    }
}
ProjectTaskKanbanShortcutsDialog.template = "project.ProjectTaskKanbanShortcutsDialog";
ProjectTaskKanbanShortcutsDialog.components = { Dialog };
ProjectTaskKanbanShortcutsDialog.title = _lt("Quick Creation Tips");
