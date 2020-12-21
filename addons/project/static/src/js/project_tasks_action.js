odoo.define("project.ProjectAction", function (require) {
    "use strict";

    const AbstractAction = require("web.AbstractAction");
    const core = require("web.core");
    const ProjectControlPanel = require("project.ProjectControlPanel");

    const _t = core._t;

    const ProjectAction = AbstractAction.extend({
        config: Object.assign({}, AbstractAction.prototype.config, {
            ControlPanel: ProjectControlPanel,
        }),
        hasControlPanel:true,
        loadControlPanel:true,
        withSearchBar: true,
        searchMenuTypes: ['filter', 'groupBy', 'favorite'],
        /**
         * @override
         */
        init(parent, action, options) {
            this._super.apply(this, arguments);
            this.tag = action.tag;
            this.res_id = action.params.active_id;

            this.action = action;
            this.actionManager = parent;
            this.odoo_context = action.context;
            this.searchModelConfig.modelName = 'project.task';
            this.options = options;

            this.projectName = false;
        },
        willStart: function () {
            var self = this;
            const promises = [];
            promises.push(this._super.apply(this, arguments));
            promises.push(this._rpc({
                model: "project.project",
                method: "search_read",
                fields: ["name"],
                domain: [["id", "=", this.res_id]],
                limit: 1,
            }).then(name => {
                self.projectName = name[0].name;
            }));
            return Promise.all(promises);
            
        },

        /**
         * @override
         */
        async start() {
            await this._super.apply(this, arguments);
            this._setTitle(this.projectName);
        },

        /**
         * @override
         */
        getTitle() {
            // Return "Project" as the action name while the project name is not loaded or
            // the actual project name once loaded.
            return this.projectName === false ? _t("Project") : this.projectName;
        },

        /**
         * Open a project
         */
        _openProject(active_id) {
            this.displayNotification({
                type: "info",
                message: this.notificationMessage,
                sticky: false,
            });
            this.do_action(
                {
                    type: "ir.actions.client",
                    tag: this.tag,
                    params: { active_id },
                },
                { clear_breadcrumbs: false }
            );
        },
    });

    core.action_registry.add("action_project_updates", ProjectAction);

    return ProjectAction;
});
