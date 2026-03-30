/** @odoo-module ignore **/

odoo.define("kodoo_studio.ModuleForm", function (require) {
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

    class ModuleForm extends Component {
        setup() {
            this.state = useState({
                module: null,
                form: {
                    name: "",
                    technical_name: "",
                    version: "",
                    depends: "",
                },
                dirty: false,
                saving: false,
                loading: false,
                error: null,
            });

            onMounted(() => this.loadModule(this.props.moduleId));
            onWillUpdateProps((nextProps) => {
                if (
                    nextProps.moduleId !== this.props.moduleId ||
                    nextProps.reloadStamp !== this.props.reloadStamp
                ) {
                    return this.loadModule(nextProps.moduleId);
                }
            });
        }

        async loadModule(moduleId) {
            this.state.loading = true;
            this.state.error = null;
            this.state.dirty = false;
            if (!moduleId) {
                this.state.module = null;
                this.state.loading = false;
                return;
            }
            try {
                const moduleRecord = await forgeApi.getModule(moduleId);
                this.state.module = moduleRecord;
                this.state.form.name = moduleRecord ? moduleRecord.name || "" : "";
                this.state.form.technical_name = moduleRecord ? moduleRecord.technical_name || "" : "";
                this.state.form.version = moduleRecord ? moduleRecord.version || "" : "";
                this.state.form.depends = moduleRecord ? moduleRecord.depends || "" : "";
            } catch (error) {
                this.state.error = error.message || "Could not load module.";
                this.state.module = null;
            } finally {
                this.state.loading = false;
            }
        }

        markDirty() {
            this.state.dirty = true;
        }

        async save() {
            if (!this.state.module) {
                return;
            }
            this.state.saving = true;
            this.state.error = null;
            try {
                const updated = await forgeApi.saveModule(this.state.module.id, {
                    name: this.state.form.name,
                    technical_name: this.state.form.technical_name,
                    version: this.state.form.version,
                    depends: this.state.form.depends,
                });
                this.state.module = updated;
                this.state.dirty = false;
                if (this.props.onModuleUpdated) {
                    this.props.onModuleUpdated(updated);
                }
            } catch (error) {
                this.state.error = error.message || "Could not save module.";
            } finally {
                this.state.saving = false;
            }
        }

        stateClass() {
            const state = this.state.module && this.state.module.state ? this.state.module.state : "draft";
            return `o_kodoo_studio__state o_kodoo_studio__state--${state}`;
        }
    }

    ModuleForm.template = "ModuleForm";
    namespace.components.ModuleForm = ModuleForm;
    owl.registry.add("ModuleForm", ModuleForm);
    return ModuleForm;
});
