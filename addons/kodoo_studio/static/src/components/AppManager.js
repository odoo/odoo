/** @odoo-module ignore **/

odoo.define("kodoo_studio.AppManager", function (require) {
    "use strict";

    const { Component, onMounted, onWillUpdateProps, useState } = owl;
    const forgeApi = require("kodoo_studio.forge_api");

    const namespace = window.kodooStudio = window.kodooStudio || {};
    namespace.components = namespace.components || {};
    if (!owl.registry) {
        owl.registry = {
            content: {},
            add(name, value) {
                this.content[name] = value;
                return value;
            },
            get(name) {
                return this.content[name];
            },
        };
    }

    class AppManager extends Component {
        setup() {
            this.state = useState({
                apps: [],
                expanded: {},
                loading: false,
                dialog: null,
                error: null,
                appForm: {
                    name: "",
                    technical_name: "",
                },
                moduleForm: {
                    app_id: null,
                    name: "",
                    technical_name: "",
                    depends: "base",
                },
            });

            onMounted(() => this.loadApps());
            onWillUpdateProps((nextProps) => {
                if (nextProps.reloadStamp !== this.props.reloadStamp) {
                    return this.loadApps();
                }
            });
        }

        get selectedModuleId() {
            return this.props.selectedModuleId || null;
        }

        async loadApps(options) {
            this.state.loading = true;
            this.state.error = null;
            const previousExpanded = Object.assign({}, this.state.expanded);
            try {
                const apps = await forgeApi.listApps();
                const withModules = await Promise.all(
                    (apps || []).map(async (app) => {
                        const modules = await forgeApi.listModules(app.id);
                        return Object.assign({}, app, { modules: modules || [] });
                    })
                );
                this.state.apps = withModules;

                const nextExpanded = {};
                for (const app of withModules) {
                    nextExpanded[app.id] = previousExpanded[app.id] || false;
                }

                if (options && options.expandAppId) {
                    nextExpanded[options.expandAppId] = true;
                }
                this.state.expanded = nextExpanded;
            } catch (error) {
                this.state.error = error.message || "Could not load apps.";
            } finally {
                this.state.loading = false;
            }
        }

        toggleApp(appId) {
            this.state.expanded[appId] = !this.state.expanded[appId];
        }

        openAppDialog() {
            this.state.dialog = "app";
            this.state.appForm.name = "";
            this.state.appForm.technical_name = "";
        }

        openModuleDialog(appId) {
            this.state.dialog = "module";
            this.state.moduleForm.app_id = appId;
            this.state.moduleForm.name = "";
            this.state.moduleForm.technical_name = "";
            this.state.moduleForm.depends = "base";
        }

        closeDialog() {
            this.state.dialog = null;
        }

        async createApp() {
            try {
                const newAppId = await forgeApi.createApp({
                    name: this.state.appForm.name,
                    technical_name: this.state.appForm.technical_name,
                });
                this.state.dialog = null;
                await this.loadApps({ expandAppId: newAppId });
            } catch (error) {
                this.state.error = error.message || "Could not create app.";
            }
        }

        async createModule() {
            try {
                const newModuleId = await forgeApi.createModule({
                    app_id: this.state.moduleForm.app_id,
                    name: this.state.moduleForm.name,
                    technical_name: this.state.moduleForm.technical_name,
                    depends: this.state.moduleForm.depends || "base",
                });
                this.state.dialog = null;
                await this.loadApps({ expandAppId: this.state.moduleForm.app_id });
                if (this.props.onSelectModule) {
                    this.props.onSelectModule(newModuleId, this.state.moduleForm.app_id);
                }
            } catch (error) {
                this.state.error = error.message || "Could not create module.";
            }
        }

        onSelectModule(moduleId, appId) {
            if (this.props.onSelectModule) {
                this.props.onSelectModule(moduleId, appId);
            }
        }

        moduleStateClass(state) {
            return `o_kodoo_studio__state o_kodoo_studio__state--${state || "draft"}`;
        }
    }

    AppManager.template = "AppManager";
    namespace.components.AppManager = AppManager;
    owl.registry.add("AppManager", AppManager);
    return AppManager;
});
