/** @odoo-module ignore **/

odoo.define("kodoo_studio.PipelinePanel", function (require) {
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

    function emptyLoading() {
        return {
            validate: false,
            build: false,
            diff: false,
            publish: false,
            snapshot: false,
        };
    }

    function defaultResults() {
        return {
            validate: null,
            build: null,
            publish: null,
            snapshot: null,
        };
    }

    function categoryLabel(issue) {
        const rule = String(issue.rule || "");
        if (rule.startsWith("module.")) {
            return "Module";
        }
        if (rule.startsWith("model.")) {
            return "Model";
        }
        if (rule.startsWith("field.")) {
            return "Field";
        }
        if (rule.startsWith("view.")) {
            return "View";
        }
        if (rule.startsWith("menu.")) {
            return "Menu";
        }
        if (rule.startsWith("action.")) {
            return "Action";
        }
        if (rule.startsWith("group.") || rule.startsWith("access.")) {
            return "Security";
        }
        if (rule.startsWith("xmlid.")) {
            return "XML";
        }
        if (rule.startsWith("depends.") || rule.startsWith("module.depends")) {
            return "Dependency";
        }
        return "General";
    }

    function renderConflictDiff(conflict) {
        return [
            "--- generated",
            conflict.generated_content || "",
            "+++ current",
            conflict.current_content || "",
        ].join("\n");
    }

    class PipelinePanel extends Component {
        setup() {
            this.state = useState({
                module: null,
                loading: emptyLoading(),
                results: defaultResults(),
                diffResult: null,
                snapshots: [],
                conflicts: [],
                conflictWarnings: [],
                showConflicts: false,
                expandedConflictKeys: {},
                publishMode: "export",
                publishConfirm: false,
                snapshotName: "",
                latestBuild: null,
                error: null,
            });

            onMounted(() => this.loadPanel(this.props.moduleId, { resetResults: true }));
            onWillUpdateProps((nextProps) => {
                if (nextProps.moduleId !== this.props.moduleId) {
                    return this.loadPanel(nextProps.moduleId, { resetResults: true });
                }
            });
        }

        async loadPanel(moduleId, options) {
            this.state.error = null;
            if (options && options.resetResults) {
                this.state.results = defaultResults();
                this.state.publishConfirm = false;
                this.state.showConflicts = false;
                this.state.expandedConflictKeys = {};
                this.state.snapshotName = this.defaultSnapshotName();
            }
            if (!moduleId) {
                this.state.module = null;
                this.state.diffResult = null;
                this.state.snapshots = [];
                this.state.conflicts = [];
                this.state.conflictWarnings = [];
                this.state.latestBuild = null;
                return;
            }
            try {
                const payloads = await Promise.all([
                    forgeApi.getModule(moduleId),
                    forgeApi.diff(moduleId),
                    forgeApi.listSnapshots(moduleId),
                    forgeApi.conflicts(moduleId),
                    forgeApi.listBuilds(moduleId),
                ]);
                this.state.module = payloads[0];
                this.state.diffResult = payloads[1];
                this.state.snapshots = payloads[2] || [];
                this.state.conflicts = (payloads[3] && payloads[3].conflicts) || [];
                this.state.conflictWarnings = (payloads[3] && payloads[3].warnings) || [];
                this.state.latestBuild = payloads[4] && payloads[4].length ? payloads[4][0] : null;
            } catch (error) {
                this.state.error = error.message || "Could not load pipeline state.";
            }
        }

        defaultSnapshotName() {
            return `snapshot-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}`;
        }

        async refreshState() {
            await this.loadPanel(this.props.moduleId);
            if (this.props.onModuleChanged) {
                this.props.onModuleChanged();
            }
        }

        startLoading(name) {
            this.state.loading[name] = true;
        }

        stopLoading(name) {
            this.state.loading[name] = false;
        }

        async runValidate() {
            if (!this.props.moduleId) {
                return;
            }
            this.startLoading("validate");
            this.state.error = null;
            try {
                this.state.results.validate = await forgeApi.validate(this.props.moduleId);
                this.state.module = await forgeApi.getModule(this.props.moduleId);
            } catch (error) {
                this.state.error = error.message || "Validation failed.";
            } finally {
                this.stopLoading("validate");
            }
        }

        async runBuild() {
            if (!this.props.moduleId) {
                return;
            }
            this.startLoading("build");
            this.state.error = null;
            try {
                this.state.results.build = await forgeApi.build(this.props.moduleId);
            } catch (error) {
                if (error.payload && error.payload.detail) {
                    this.state.results.build = error.payload.detail;
                    if (error.payload.detail.errors) {
                        this.state.results.validate = {
                            valid: false,
                            errors: error.payload.detail.errors,
                        };
                    }
                } else {
                    this.state.error = error.message || "Build failed.";
                }
            } finally {
                this.stopLoading("build");
                await this.refreshState();
                if (this.props.onOpenTerminal) {
                    this.props.onOpenTerminal();
                }
            }
        }

        async runDiff() {
            if (!this.props.moduleId) {
                return;
            }
            this.startLoading("diff");
            this.state.error = null;
            try {
                this.state.diffResult = await forgeApi.diff(this.props.moduleId);
            } catch (error) {
                this.state.error = error.message || "Diff failed.";
            } finally {
                this.stopLoading("diff");
            }
        }

        askPublish() {
            this.state.publishConfirm = true;
        }

        cancelPublish() {
            this.state.publishConfirm = false;
        }

        async confirmPublish() {
            if (!this.props.moduleId) {
                return;
            }
            this.startLoading("publish");
            this.state.error = null;
            this.state.publishConfirm = false;
            try {
                this.state.results.publish = await forgeApi.publish(
                    this.props.moduleId,
                    this.state.publishMode
                );
            } catch (error) {
                this.state.error = error.message || "Publish failed.";
            } finally {
                this.stopLoading("publish");
                await this.refreshState();
                if (this.props.onOpenTerminal) {
                    this.props.onOpenTerminal();
                }
            }
        }

        async runSnapshot() {
            if (!this.props.moduleId) {
                return;
            }
            this.startLoading("snapshot");
            this.state.error = null;
            try {
                this.state.results.snapshot = await forgeApi.snapshot(
                    this.props.moduleId,
                    this.state.snapshotName || this.defaultSnapshotName()
                );
                this.state.snapshotName = this.defaultSnapshotName();
            } catch (error) {
                this.state.error = error.message || "Snapshot failed.";
            } finally {
                this.stopLoading("snapshot");
                await this.refreshState();
            }
        }

        async rollback(snapshotId) {
            if (!this.props.moduleId) {
                return;
            }
            this.state.error = null;
            try {
                await forgeApi.rollback(this.props.moduleId, snapshotId);
            } catch (error) {
                this.state.error = error.message || "Rollback failed.";
            } finally {
                await this.refreshState();
            }
        }

        toggleConflicts() {
            this.state.showConflicts = !this.state.showConflicts;
        }

        toggleConflictDiff(conflict) {
            const key = this.conflictKey(conflict);
            this.state.expandedConflictKeys[key] = !this.state.expandedConflictKeys[key];
        }

        conflictKey(conflict) {
            return `${conflict.artifact_id || "0"}:${conflict.block_id || "__file__"}`;
        }

        isConflictExpanded(conflict) {
            return !!this.state.expandedConflictKeys[this.conflictKey(conflict)];
        }

        groupedValidationErrors() {
            const result = {};
            const payload = this.state.results.validate;
            const errors = payload && payload.errors ? payload.errors : [];
            for (const issue of errors) {
                const category = categoryLabel(issue);
                result[category] = result[category] || [];
                result[category].push(issue);
            }
            return result;
        }

        groupedValidationEntries() {
            return Object.entries(this.groupedValidationErrors());
        }

        diffItems() {
            const items = [];
            const diff = this.state.diffResult || {};
            for (const path of diff.added || []) {
                items.push({ icon: "+", path: path, type: "added" });
            }
            for (const path of diff.changed || []) {
                items.push({ icon: "~", path: path, type: "changed" });
            }
            for (const path of diff.removed || []) {
                items.push({ icon: "-", path: path, type: "removed" });
            }
            return items;
        }

        lastSnapshot() {
            return this.state.snapshots.length ? this.state.snapshots[0] : null;
        }

        moduleStateClass() {
            const state = this.state.module && this.state.module.state ? this.state.module.state : "draft";
            return `o_kodoo_studio__state o_kodoo_studio__state--${state}`;
        }

        loadingClass(name) {
            return this.state.loading[name] ? "disabled" : "";
        }

        formatDate(value) {
            if (!value) {
                return "Pending";
            }
            return new Date(value).toLocaleString("pt-BR");
        }

        conflictDiff(conflict) {
            return renderConflictDiff(conflict);
        }
    }

    PipelinePanel.template = "PipelinePanel";
    namespace.components.PipelinePanel = PipelinePanel;
    owl.registry.add("PipelinePanel", PipelinePanel);
    return PipelinePanel;
});
