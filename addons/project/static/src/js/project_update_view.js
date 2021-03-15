odoo.define('project.ProjectUpdateView', function (require) {
    "use strict";

    const { _lt } = require('web.core');
    const KanbanController = require('web.KanbanController');
    const KanbanView = require('web.KanbanView');
    const { ComponentAdapter, ComponentWrapper } = require('web.OwlCompatibility');
    const viewRegistry = require('web.view_registry');
    const { FormViewDialog } = require('web.view_dialogs');
    const { Component } = owl;
    const { useState, useRef } = owl.hooks;


    class FormViewDialogComponentAdapter extends ComponentAdapter {
        renderWidget() {
            // Ensure the dialog is properly reconstructed. Without this line, it is
            // impossible to open the dialog again after having it closed a first
            // time, because the DOM of the dialog has disappeared.
            return this.willStart();
        }
    }

    const components = {
        FormViewDialogComponentAdapter,
    };

    class AddMilestone extends Component {
        constructor() {
            super(...arguments);
            this.contextValue = Object.assign({}, {
                'default_project_id': this.props.context.active_id,
            }, this.props.context);
            this.FormViewDialog = FormViewDialog;
            this._dialogRef = useRef('dialog');
            this._isDialogOpen = false;
            this._onDialogSaved = this._onDialogSaved.bind(this);
        }

        get NEW_PROJECT_MILESTONE() {
            return _lt("New Project Milestone");
        }

        get context() {
            return this.contextValue;
        }

        set context(value) {
            this.contextValue = Object.assign({}, {
                'default_project_id': value.active_id,
            }, value);
        }

        async onAddMilestoneClick() {
            if (!this._isDialogOpen) {
                await this._dialogRef.comp.renderWidget();
                this._isDialogOpen = true;
                this._dialogRef.comp.widget.on('closed', this, () => {
                    this._isDialogOpen = false;
                });
                this._dialogRef.comp.widget.open();
            }
        }

        _onDialogSaved() {
            this.__owl__.parent.willUpdateProps();
        }
    }

    Object.assign(AddMilestone, {
        components,
        template: 'project.AddMilestone',
    });

    class ProjectUpdateSidePanel extends owl.Component {
        constructor() {
            super(...arguments);
            this.context = this.props.action.context;
            this.domain = this.props.action.domain;
            this.project_id = this.context.active_id;
            this.tasks = useState({
                data: {
                    open_tasks: 0,
                    updated_tasks: 0,
                    older_last_update: null,
                    default_action: {},
                }
            });
            this.milestones = useState({
                data: [],
                default_action: {},
            });
        }

        async willStart() {
            await super.willStart(...arguments);
            await this._loadQwebContext();
        }

        async willUpdateProps() {
            await super.willUpdateProps(...arguments);
            await this._loadQwebContext();
        }

        async _loadQwebContext() {
            const data = await this.rpc({
                model: 'project.project',
                method: 'get_panel_data',
                args: [this.project_id],
            });
            this.tasks.data = data.tasks;
            this.milestones.data = data.milestones;

            // we need to map view_mode to views as we retrieve the action
            // from server to be as serverside as possible.
            const views = this.tasks.data.default_action.view_mode.split(",");
            this.tasks.data.default_action.views = [];
            for (let view of views) {
                this.tasks.data.default_action.views.push([false, view]);
            }
        }

        onOpenTaskClick() {
            const options = {
                name: _lt("Open Tasks").toString(),
                context: this.context,
                domain: this.domain.concat([["stage_id.fold", "=", false]]),
            };
            this._doAction(Object.assign({}, this.tasks.data.default_action, options));
        }

        onUpdatedTaskClick() {
            const options = {
                name: _lt("Recently Updated Tasks (last 30 days)").toString(),
                context: this.context,
                domain: this.domain.concat([["write_date", ">", this.tasks.data.older_last_update]]),
            };
            this._doAction(Object.assign({}, this.tasks.data.default_action, options));
        }

        async onMilestoneClick(event) {
            const $checkbox = $(event.currentTarget);
            const value = $checkbox.data('value');
            const id = $checkbox.data('id');
            if (!id || value === undefined) {
                return;
            }
            const $i = $checkbox.find('i');
            $i.removeClass(value ? 'fa-check-square' : 'fa-square-o').addClass('fa-spinner fa-spin');
            await this.rpc({
                model: 'project.milestone',
                method: 'write',
                args: [[id], {is_done: !value}],
            });
            $checkbox.data('value', value ? 0 : 1);
            $checkbox.attr('data-value', value ? 0 : 1);
            $i.removeClass('fa-spinner fa-spin').addClass(!value ? 'fa-check-square' : 'fa-square-o');
        }

        _doAction(action) {
            this.trigger('do-action', {
                action: action,
            });
        }
    }

    ProjectUpdateSidePanel.template = "project.KanbanSidePanel";
    ProjectUpdateSidePanel.components = {AddMilestone};

    const ProjectUpdateKanbanController = KanbanController.extend({
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.rightSidePanel = params.rightSidePanel;
        },
        /**
         * @override
         */
        start: async function () {
            const promises = [this._super(...arguments)];
            this._rightPanelWrapper = new ComponentWrapper(this, this.rightSidePanel.Component, this.rightSidePanel.props);
            const content = this.el.querySelector(':scope .o_content');
            content.classList.add('o_controller_with_rightpanel');
            promises.push(this._rightPanelWrapper.mount(content, { position: 'last-child' }));
            await Promise.all(promises);
        },
        async _update() {
            this._rightPanelWrapper.update(this.rightSidePanel.props);
            await this._super.apply(this, arguments);
        }
    });

    const ProjectUpdateKanbanView = KanbanView.extend({
        searchMenuTypes: ['filter', 'favorite'],
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: ProjectUpdateKanbanController,
            RightSidePanel: ProjectUpdateSidePanel,
        }),
        _createSearchModel: function (params) {
            const result = this._super.apply(this, arguments);
            const props = {
                action: params.action,
            };
            this.controllerParams.rightSidePanel = {
                Component: this.config.RightSidePanel,
                props: props,
            };
            return result;
        }
    });

    viewRegistry.add('project_update_kanban', ProjectUpdateKanbanView);

    return ProjectUpdateKanbanView;
});
