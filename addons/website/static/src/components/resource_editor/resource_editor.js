/** @odoo-module */

import { CodeEditor } from "@web/core/code_editor/code_editor";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { sortBy } from "@web/core/utils/arrays";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";

import { ResourceEditorWarningOverlay } from "./resource_editor_warning";
import { checkSCSS, checkXML, formatXML } from "./utils";

import { Component, onWillUnmount, onWillStart, reactive, useRef, useState } from "@odoo/owl";

const BUNDLES_RESTRICTION = [
    "web.assets_frontend",
    "web.assets_frontend_minimal",
    "web.assets_frontend_lazy",
];

export class ResourceEditor extends Component {
    static components = {
        ResourceEditorWarningOverlay,
        CodeEditor,
        Dropdown,
        CheckboxItem,
        DropdownItem,
        SelectMenu,
    };
    static template = "website.ResourceEditor";
    static props = {
        close: { type: Function, optional: true },
    };
    static defaultProps = {
        close: () => {},
    };

    setup() {
        this.website = useService("website");
        this.user = useService("user");
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.dialog = useService("dialog");

        this.keepLast = new KeepLast();

        this.editorRef = useRef("editor");

        this.debug = this.env.debug;
        this.viewKey =
            this.website.pageDocument &&
            this.website.pageDocument.documentElement.dataset.viewXmlid;

        this.types = {
            xml: "XML (HTML)",
            scss: "SCSS (CSS)",
            js: "JS",
        };
        this.xmlFilters = {
            views: _t("Only Views"),
            all: _t("Views and Assets bundles"),
        };
        this.scssFilters = {
            custom: _t("Only Custom SCSS Files"),
            restricted: _t("Only Page SCSS Files"),
            all: _t("All SCSS Files"),
        };
        this.state = useState({
            type: "xml",
            xmlFilter: "views",
            scssFilter: "custom",
            currentResource: false,
            showEditWarning: true,
            resources: {
                xml: {},
                js: {},
                scss: {},
            },
            sortedXML: [],
            sortedSCSS: [],
            sortedJS: [],
            saving: false,
        });

        let showErrorInterval;
        this.errors = reactive([], () => {
            clearInterval(showErrorInterval);
            if (this.errors.length) {
                this.showErrorLine();
                // The ace library updates its content asynchronously, and sometimes
                // at unexpected moments, so we consistently re-apply the error indicators
                // when they are errors. This is kind of a hack, but it works.
                showErrorInterval = setInterval(() => this.showErrorLine(), 500);
            } else {
                this.clearErrorLine();
            }
        });
        onWillUnmount(() => clearInterval(showErrorInterval));

        onWillStart(async () => this.loadResources());
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get context() {
        return {
            ...this.user.context,
            website_id: this.website.currentWebsite.id,
        };
    }

    get resourceInfo() {
        if (!this.state.currentResource) {
            return "";
        }
        if (this.state.type === "xml") {
            return _t("Template ID: %s", this.state.currentResource.key);
        } else if (this.state.type === "scss") {
            return _t("SCSS file: %s", this.state.currentResource.url);
        } else {
            return _t("JS file: %s", this.state.currentResource.url);
        }
    }

    get selectMenuProps() {
        const props = {
            onSelect: (value) => {
                this.state.currentResource = this.state.resources[this.state.type][value];
            },
            autoSort: false,
            required: true,
        };
        if (this.state.type === "xml") {
            const choices = this.state.sortedXML.map((view) => {
                return { value: view.id, label: view.label };
            });
            const value = this.state.currentResource?.id;
            return { ...props, choices, value };
        } else {
            const { type, sortedSCSS, sortedJS } = this.state;
            const bundles = type === "scss" ? sortedSCSS : sortedJS;
            const groups = bundles.map(([name, files]) => {
                const choices = files.map((file) => ({ value: file.url, label: file.label }));
                return { label: name, choices };
            });
            const value = this.state.currentResource?.url;
            return { ...props, groups, value };
        }
    }

    // -------------------------------------------------------------------------
    // Methods
    // -------------------------------------------------------------------------

    /**
     * Checks resource is customized or not.
     *
     * @param {string} url
     * @returns {boolean}
     */
    isCustomResource(url) {
        // TODO we should be able to detect if the XML template is customized
        // to not show the warning in that case
        if (this.state.type === "scss") {
            return this.state.resources.scss[url].customized;
        } else if (this.state.type === "js") {
            return this.state.resources.js[url].customized;
        }
        return false;
    }

    async loadResources() {
        const resources = await this.keepLast.add(
            this.rpc("/web_editor/get_assets_editor_resources", {
                key: this.viewKey,
                bundles: this.state.xmlFilter === "all",
                bundles_restriction: BUNDLES_RESTRICTION,
                only_user_custom_files: this.state.scssFilter === "custom",
            })
        );
        this.state.resources = { xml: {}, js: {}, scss: {} };
        this.processResources(resources.views || [], "xml");
        this.processResources(resources.scss || [], "scss");
        this.processResources(resources.js || [], "js");
        const type = this.state.type;
        if (this.state.currentResource) {
            this.state.currentResource = this.state.resources[type][this.state.currentResource.id];
        }
        if (!this.state.currentResource) {
            this.setDefaultFile();
        }
        this.errors.length = 0;
    }

    processResources(resources, type) {
        if (type === "xml") {
            // Only keep the active views and index them by ID.
            const indexedById = {};
            resources
                .filter((view) => view.active)
                .forEach((view) => {
                    view.type = "xml";
                    indexedById[view.id] = view;
                });
            Object.assign(this.state.resources.xml, indexedById);

            // Initialize a 0 level for each view and assign them an array containing their children.
            const roots = [];
            Object.values(this.state.resources.xml).forEach((view) => {
                view.level = 0;
                view.children = [];
            });
            Object.values(this.state.resources.xml).forEach((view) => {
                const parentId = view.inherit_id[0];
                const parent = parentId && this.state.resources.xml[parentId];
                if (parent) {
                    parent.children.push(view);
                } else {
                    roots.push(view);
                }
            });

            // Assign the correct level based on children key and save a sorted array where
            // each view is followed by their children.
            const sortedXML = [];
            const visit = (view, level) => {
                view.level = level;
                sortedXML.push(view);
                view.children.forEach((child) => {
                    visit(child, level + 1);
                });
            };
            roots.forEach((root) => {
                visit(root, 0);
            });
            this.state.sortedXML = sortedXML;

            // Compute labels
            Object.values(this.state.resources.xml).forEach((view) => {
                view.label = `${"-".repeat(view.level)} ${view.name}`;
                if (this.debug && view.xml_id) {
                    view.label += ` (${view.xml_id})`;
                }
            });
        } else if (type === "scss" || type === "js") {
            // The received scss or js data is already sorted by bundle and DOM order
            if (type === "scss") {
                this.state.sortedSCSS = resources;
            } else {
                this.state.sortedJS = resources;
            }

            // Store the URL ungrouped by bundle and use the URL as key (resource ID)
            resources.forEach(([bundle, files]) => {
                const indexedByUrl = {};
                files.forEach((file) => {
                    // Compute labels
                    file.label = file.url.split("/").at(-1).split(".")[0];
                    if (this.debug) {
                        file.label += ` (${file.url})`;
                    }

                    file.bundle = bundle;
                    file.id = file.url; // for consistency with xml resources
                    file.type = type;
                    indexedByUrl[file.url] = file;
                });
                if (type === "scss") {
                    Object.assign(this.state.resources.scss, indexedByUrl);
                } else {
                    Object.assign(this.state.resources.js, indexedByUrl);
                }
            });
        }
    }

    /**
     * Forces the current scss/js file identified by its url to be reset to the way
     * it was before the user started editing it.
     *
     * @todo views (xml) reset is not supported yet
     *
     * @returns {Promise}
     */
    async resetResource() {
        if (this.state.type === "xml") {
            throw new Error(_t("Reseting views is not supported yet"));
        }
        const resource = this.state.currentResource;
        await this.orm.call("web_editor.assets", "reset_asset", [resource.url, resource.bundle], {
            context: this.context,
        });
        await this.loadResources();
        this.website.contentWindow.location.reload();
    }

    async saveResources() {
        const { js, scss, xml } = this.state.resources;
        const toSave = {
            js: Object.values(js).filter((r) => r.dirty),
            scss: Object.values(scss).filter((r) => r.dirty),
            // child views first as COW on a parent would delete them
            xml: sortBy(
                Object.values(xml).filter((r) => r.dirty),
                "id"
            ).reverse(),
        };

        for (const [type, resources] of Object.entries(toSave)) {
            for (let i = 0; i < resources.length; i++) {
                const arch = resources[i].arch;
                const { isValid, error } = type === "xml" ? checkXML(arch) : checkSCSS(arch);
                if (!isValid) {
                    this.errors.push({ error, resource: resources[i] });
                }
            }
        }
        if (this.errors.length) {
            // switch to the first resource in error if the current has no error
            if (
                !this.errors
                    .map(({ resource }) => resource.id)
                    .includes(this.state.currentResource.id)
            ) {
                this.state.currentResource = this.errors[0].resource;
                this.state.type = this.errors[0].resource.type;
            }
            return;
        }

        // sequentially save all resources
        for (const [type, resources] of Object.entries(toSave)) {
            for (const resource of resources) {
                if (type === "xml") {
                    await this.saveXML(resource);
                } else {
                    await this.saveSCSSorJS(resource);
                }
            }
        }
        await this.loadResources();
        this.website.contentWindow.location.reload();
    }

    /**
     * Saves a unique SCSS or JS file.
     *
     * @private
     * @param {Object} resource a SCSS or JS file to save
     * @return {Promise} indicates if the save is finished or if an error occured.
     */
    async saveSCSSorJS(resource) {
        const { url, arch } = resource;
        const isJSFile = String(url).endsWith(".js");
        const bundle = isJSFile
            ? this.state.resources.js[url].bundle
            : this.state.resources.scss[url].bundle;
        const fileType = isJSFile ? "js" : "scss";
        const params = [url, bundle, arch, fileType];
        await this.orm.call("web_editor.assets", "save_asset", params, { context: this.context });
        delete resource.dirty;
    }

    /**
     * Saves a unique XML view.
     *
     * @param {Object} resource an xml view to save
     * @returns {Promise} indicates if the save is finished or if an error occured.
     */
    async saveXML(resource) {
        const { id, arch } = resource;
        const context = { ...this.context, lang: false };
        await this.orm.write("ir.ui.view", [id], { arch }, { context });
        delete resource.dirty;
    }

    setDefaultFile() {
        if (this.state.type === "xml") {
            const views = Object.values(this.state.resources.xml);
            let view = views.find((view) => [view.id, view.xml_id].includes(this.viewKey));
            if (!view) {
                view = views.find((view) => view.key === this.viewKey);
            }
            this.state.currentResource = view || this.state.sortedXML[0] || false;
        } else if (this.state.type === "scss") {
            // By default show the user_custom_rules.scss one as some people
            // would write rules in user_custom_bootstrap_overridden.scss
            // otherwise, not reading the comment inside explaining how that
            // file should be used.
            this.state.currentResource =
                this.state.resources.scss["/website/static/src/scss/user_custom_rules.scss"];
        } else {
            this.state.currentResource =
                this.state.sortedJS.map(([_, files]) => files).flat()[0] || false;
        }
    }

    showErrorLine() {
        const resourceId = this.state.currentResource.id;
        const error = this.errors.find(({ resource }) => resource.id === resourceId)?.error;
        if (error) {
            const { line, message } = error;
            const gutterCell = this.editorRef.el.querySelectorAll(".ace_gutter-cell")[line - 1];
            if (gutterCell && !gutterCell.classList.contains("o_error")) {
                gutterCell.classList.add("o_error");
                gutterCell.setAttribute("data-tooltip", message);
                gutterCell.setAttribute("data-tooltip-position", "left");
            }
        }
    }

    clearErrorLine() {
        const allGutterCells = this.editorRef.el.querySelectorAll(".ace_gutter-cell");
        for (const gutterCell of allGutterCells) {
            gutterCell.classList.remove("o_error");
            gutterCell.removeAttribute("data-tooltip");
            gutterCell.removeAttribute("data-tooltip-position");
        }
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    onEditorChange(value) {
        const currentResource = this.state.currentResource;
        currentResource.arch = value;
        currentResource.dirty = true;
        this.errors.length = 0;
    }

    /**
     * @param {"xml"|"scss"|"js"} type
     */
    onFileTypeChange(type) {
        if (type !== this.state.type) {
            this.state.type = type;
            this.setDefaultFile();
        }
    }

    /**
     * @param {"xml"|"scss"} type
     * @param {string} filter
     */
    onFilterChange(type, filter) {
        if (type === "scss") {
            this.state.scssFilter = filter;
        } else if (type === "xml") {
            this.state.xmlFilter = filter;
        }
        this.loadResources();
    }

    onFormat() {
        if (this.state.type === "xml") {
            const { isValid, error } = checkXML(this.state.currentResource.arch);
            if (isValid) {
                this.state.currentResource.arch = formatXML(this.state.currentResource.arch);
            } else {
                this.errors.push({ error, resource: this.state.currentResource });
            }
        }
    }

    onReset() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Careful"),
            body: _t(
                "If you reset this file, all your customizations will be lost as it will be reverted to the default file."
            ),
            confirm: () => this.resetResource(),
            cancel: () => {},
        });
    }

    async onSave() {
        this.state.saving = true;
        try {
            await this.saveResources();
        } finally {
            this.state.saving = false;
        }
    }
}
