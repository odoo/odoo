/** @odoo-module ignore **/

odoo.define("kodoo_studio", function (require) {
    "use strict";

    const { Component, useState } = owl;
    const { registry } = require("@web/core/registry");
    const AppManager = require("kodoo_studio.AppManager");
    const ModuleForm = require("kodoo_studio.ModuleForm");
    const PipelinePanel = require("kodoo_studio.PipelinePanel");
    const StudioTerminal = require("kodoo_studio.StudioTerminal");

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

    class KodooStudio extends Component {
        setup() {
            this.state = useState({
                selectedAppId: null,
                selectedModuleId: null,
                terminalOpen: false,
                terminalMinimized: false,
                reloadStamp: 0,
            });
        }

        onSelectModule(moduleId, appId) {
            this.state.selectedModuleId = moduleId;
            this.state.selectedAppId = appId || null;
        }

        touchSidebar() {
            this.state.reloadStamp += 1;
        }

        onModuleUpdated() {
            this.touchSidebar();
        }

        onModuleChanged() {
            this.touchSidebar();
        }

        openTerminal() {
            this.state.terminalOpen = true;
            this.state.terminalMinimized = false;
        }

        toggleTerminal() {
            this.state.terminalOpen = !this.state.terminalOpen;
            if (this.state.terminalOpen) {
                this.state.terminalMinimized = false;
            }
        }

        minimizeTerminal() {
            this.state.terminalOpen = true;
            this.state.terminalMinimized = !this.state.terminalMinimized;
        }

        closeTerminal() {
            this.state.terminalOpen = false;
            this.state.terminalMinimized = false;
        }

        terminalOpenProp() {
            return this.state.terminalOpen && !this.state.terminalMinimized;
        }

        drawerClass() {
            if (!this.state.terminalOpen) {
                return "o_kodoo_studio__drawer o_kodoo_studio__drawer--closed";
            }
            if (this.state.terminalMinimized) {
                return "o_kodoo_studio__drawer o_kodoo_studio__drawer--minimized";
            }
            return "o_kodoo_studio__drawer o_kodoo_studio__drawer--open";
        }

        bodyClass() {
            if (this.state.terminalOpen && !this.state.terminalMinimized) {
                return "o_kodoo_studio__body has-terminal";
            }
            if (this.state.terminalOpen && this.state.terminalMinimized) {
                return "o_kodoo_studio__body has-terminal-bar";
            }
            return "o_kodoo_studio__body";
        }
    }

    KodooStudio.template = "KodooStudio";
    KodooStudio.components = {
        AppManager: AppManager,
        ModuleForm: ModuleForm,
        PipelinePanel: PipelinePanel,
        StudioTerminal: StudioTerminal,
    };

    namespace.components.KodooStudio = KodooStudio;
    owl.registry.add("KodooStudio", KodooStudio);
    registry.category("actions").add("kodoo_studio", KodooStudio, { force: true });
    return KodooStudio;
});
