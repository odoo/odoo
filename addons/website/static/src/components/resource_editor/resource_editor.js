import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { formatList } from "@web/core/l10n/utils/format_list";
import { rpc } from "@web/core/network/rpc";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { user } from "@web/core/user";
import { sortBy } from "@web/core/utils/arrays";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { usePopover } from "@web/core/popover/popover_hook";

import { locateOperations } from "./operation_map";
import { CodeEditorWithGutterMarkers } from "./code_editor_with_gutter_markers";
import { ResourceEditorWarningOverlay } from "./resource_editor_warning";
import {
    checkSCSS,
    checkXML,
    findOperationTarget,
    formatXML,
    getElementRows,
    getOperationRows,
    getOperationTargetRows,
    parseTargetArch,
} from "./utils";

import {
    Component,
    computed,
    onWillUnmount,
    onWillStart,
    useProps,
    proxy,
    signal,
    t,
    useEffect,
    usePlugin,
} from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";

const BUNDLES_RESTRICTION = [
    "web.assets_frontend",
    "web.assets_frontend_minimal",
    "web.assets_frontend_lazy",
];

const T_OPERATIONS_POPOVER_ITEM = t.object({
    view: t.object(),
    row: t.number().optional(),
    onSelect: t.function(),
});

/**
 * Popover component shown when the gutter icon is clicked. Based on the
 * context, it can show:
 * 1. The list of views that xpath the current line
 * 2. The list of views xpathed by the current line
 * Case 2 could have more than one entry if a line contains multiple xpath
 * elements (bad formatting, but it costs nothing to cover for this case).
 * Case 1 and 2 could coexist on the same line if an xpath element is target
 * of another xpath from another view.
 */
class ResourceOperationsPopover extends Component {
    static template = "website.ResourceOperationsPopover";
    props = useProps({
        row: t.number(),
        modifiedBy: t.array(T_OPERATIONS_POPOVER_ITEM),
        modifies: t.array(T_OPERATIONS_POPOVER_ITEM),
        close: t.function().optional(),
    });

    getModifiedByTitle() {
        return _t("Line %s is modified by:", this.props.row);
    }

    getModifiesTitle() {
        return _t("Line %s modifies:", this.props.row);
    }
}

export class ResourceEditor extends Component {
    static components = {
        ResourceEditorWarningOverlay,
        CodeEditorWithGutterMarkers,
        Dropdown,
        CheckboxItem,
        DropdownItem,
        SelectMenu,
    };
    static template = "website.ResourceEditor";
    props = useProps({
        close: t.function().optional(() => () => {}),
    });

    editorRef = signal.ref();

    debugMode = usePlugin(DebugModePlugin);

    setup() {
        this.website = useService("website");
        this.orm = useService("orm");
        this.dialog = useService("dialog");

        this.keepLast = new KeepLast();

        this.operationsPopover = usePopover(ResourceOperationsPopover);
        // allLocatedOperations lists the xpaths identified in *every* view
        // available in the editor (used to build the "modified by view X" and
        // "modifies view X" hints).
        this.allLocatedOperations = signal([]);
        this.operationsOutdated = signal(false);
        // debounced to avoid recalculating while the user is typing
        this.debouncedUpdateLocatedOperations = useDebounced(
            () => this.updateLocatedOperations(),
            300
        );
        this.currentParsedArch = computed(() => this.computeCurrentParsedArch());
        this.incomingOperations = computed(() => this.computeIncomingOperations());
        this.outgoingOperations = computed(() => this.computeOutgoingOperations());
        this.codeEditorMarkers = computed(() => this.computeCodeEditorMarkers());
        this.hasUnsavedChanges = computed(() => this.computeHasUnsavedChanges());
        // the row to reveal in the code editor (see `CodeEditorWithGutterMarkers`).
        this.revealRow = signal(null);
        this.aceEditor = null;

        this.viewKey =
            this.website.pageDocument &&
            this.website.pageDocument.documentElement.dataset.viewXmlid;

        this.types = {
            xml: "XML (HTML)",
            scss: "SCSS (CSS)",
            js: "JS",
        };
        this.typeToCodeEditorModeMap = {
            xml: "qweb",
            scss: "scss",
            js: "javascript",
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
        this.state = proxy({
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
        this.errors = proxy([]);
        useEffect(() => {
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
            ...user.context,
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

    /**
     * @returns {{label: string, tooltip: string}|null} how the current view
     *  relates to the current website: a base view, a copy of a base view
     *  for the website (COW), or a view which only exists on the website.
     *  Null if the current resource is not a view.
     */
    getWebsiteStatusInfo() {
        const resource = this.state.currentResource;
        if (this.state.type !== "xml" || !resource) {
            return null;
        }
        switch (resource.website_status) {
            case "base":
                return {
                    label: _t("Base view"),
                    tooltip: _t(
                        "Saving this view creates a copy (COW) that only applies to the current website. The base view is not changed."
                    ),
                };
            case "copy":
                return {
                    label: _t("Website copy (COW) of a base view"),
                    tooltip: _t(
                        "This copy only applies to the current website. Saving changes it, not the base view."
                    ),
                };
            case "website":
                return {
                    label: _t("Website-only view"),
                    tooltip: _t("This view only exists on the current website."),
                };
            default:
                return null;
        }
    }

    /**
     * @returns {{root: Element, operations: Element[]|null}|null} the parsed
     *  arch of the current view (see `parseTargetArch`), or null if the
     *  current resource is not a view or its arch is not well-formed
     */
    computeCurrentParsedArch() {
        const resource = this.state.currentResource;
        if (this.state.type !== "xml" || !resource) {
            return null;
        }
        return parseTargetArch(resource);
    }

    /**
     * The operations of other views on the current view.
     * `targetRow` is 0-indexed. Null if the target is not found (e.g.: we
     * parsed an xpath targetting this view, but the target element could not
     * be located). Undefined if the arch is not well-formed or if the flag
     * `operationsOutdated` is true.
     *
     * @returns {Object[]}
     */
    computeIncomingOperations() {
        const resource = this.state.currentResource;
        if (this.state.type !== "xml" || !resource) {
            return [];
        }
        const incoming = this.allLocatedOperations().filter(
            ({ targetId }) => targetId === resource.id
        );
        if (!incoming.length) {
            // Avoid parsing if no operations
            return incoming;
        }
        if (this.operationsOutdated()) {
            return incoming;
        }
        const parsed = this.currentParsedArch();
        if (!parsed) {
            return incoming;
        }
        const targets = incoming.map(({ operation }) =>
            findOperationTarget(parsed.root, parsed.operations, operation)
        );
        const targetRows = getElementRows(resource.arch, parsed.root, targets);
        return incoming.map((locatedOperation, index) => ({
            ...locatedOperation,
            targetRow: targetRows[index],
        }));
    }

    /**
     * The operations of the current view on other views.
     * `operationRow` is 0-indexed. Undefined if the arch is not well-formed or
     * if the flag `operationsOutdated` is true.
     *
     * @returns {Object[]}
     */
    computeOutgoingOperations() {
        const resource = this.state.currentResource;
        if (this.state.type !== "xml" || !resource) {
            return [];
        }
        const outgoing = this.allLocatedOperations().filter(({ view }) => view.id === resource.id);
        if (!outgoing.length) {
            // Avoid parsing if no operations
            return outgoing;
        }
        // If `operationsOutdated` is true, we can't trust the `index` from
        // `locateOperations` because its content may not be correct anymore.
        // In this case, we don't return the row indexes.
        if (this.operationsOutdated()) {
            return outgoing;
        }
        const parsed = this.currentParsedArch();
        if (!parsed) {
            return outgoing;
        }
        const operations = outgoing.map(({ index }) => parsed.operations?.[index] ?? null);
        const operationRows = getElementRows(resource.arch, parsed.root, operations);
        return outgoing.map((locatedOperation, index) => ({
            ...locatedOperation,
            operationRow: operationRows[index],
        }));
    }

    /**
     * The gutter markers (passed to `CodeEditorWithGutterMarkers`) on the rows
     * that are changed by other views or change other views. Null while the
     * arch is not well-formed or the located operations are outdated.
     */
    computeCodeEditorMarkers() {
        const incoming = this.incomingOperations();
        const outgoing = this.outgoingOperations();
        if (!incoming.length && !outgoing.length) {
            return [];
        }
        if (this.operationsOutdated() || !this.currentParsedArch()) {
            return null;
        }
        const markersByRow = new Map();
        const getMarker = (row) => {
            if (!markersByRow.has(row)) {
                markersByRow.set(row, { row, viewIds: new Set(), target: false });
            }
            return markersByRow.get(row);
        };
        for (const { view, targetRow } of incoming) {
            if (targetRow !== null) {
                getMarker(targetRow).viewIds.add(view.id);
            }
        }
        for (const { operationRow } of outgoing) {
            if (operationRow !== null) {
                getMarker(operationRow).target = true;
            }
        }
        return sortBy(
            [...markersByRow.values()].map(({ row, viewIds, target }) => ({
                row,
                count: viewIds.size,
                target,
            })),
            "row"
        );
    }

    /**
     * @returns {{view: Object, operations: Object[]}[]} the views with
     *  operations on the current resource, sorted by name.
     */
    getIncomingViews() {
        const operationsByView = Map.groupBy(this.incomingOperations(), ({ view }) => view);
        return [...operationsByView]
            .map(([view, operations]) => ({ view, operations }))
            .sort((a, b) => a.view.name.localeCompare(b.view.name));
    }

    /**
     * @returns {string}
     */
    getModifiedByLabel() {
        const count = this.getIncomingViews().length;
        return count === 1 ? _t("Modified by 1 view") : _t("Modified by %s views", count);
    }

    /**
     * Describe where ``operations`` change the current arch. Return a string
     * that lists up to 3 target line numbers, followed by "and x more".
     *
     * @param {Object[]} operations items of `incomingOperations`
     * @returns {string} empty while the rows are unknown (see
     *  `incomingOperations`)
     */
    getOperationRowsLabel(operations) {
        const rows = operations.map(({ targetRow }) => targetRow);
        if (rows.includes(undefined)) {
            return "";
        }
        const lines = [...new Set(rows.filter((row) => row !== null).map((row) => row + 1))].sort(
            (a, b) => a - b
        );
        if (!lines.length) {
            return "";
        }
        if (lines.length === 1) {
            return _t("line %s", lines[0]);
        }
        const shownLines = lines.slice(0, 3).map(String);
        if (lines.length > shownLines.length) {
            shownLines.push(_t("%s more", lines.length - shownLines.length));
        }
        return _t("lines %s", formatList(shownLines));
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
            const choices = this.state.sortedXML.map((view) => ({
                value: view.id,
                label: view.label,
            }));
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
     * Tell if a resource has unsaved changes.
     *
     * @returns {boolean}
     */
    computeHasUnsavedChanges() {
        const { xml, js, scss } = this.state.resources;
        return [xml, js, scss].some((resources) =>
            Object.values(resources).some((resource) => resource.dirty)
        );
    }

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
            rpc("/website/get_assets_editor_resources", {
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

            this.allLocatedOperations.set(locateOperations(this.state.resources.xml));
            this.operationsOutdated.set(false);

            // Compute labels
            Object.values(this.state.resources.xml).forEach((view) => {
                view.label = `${"-".repeat(view.level)} ${view.name}`;
                if (this.debugMode.isActive() && view.xml_id) {
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
                    if (this.debugMode.isActive()) {
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
     * Locates the operations again, e.g., after an edit of a view.
     */
    updateLocatedOperations() {
        const resource = this.state.currentResource;
        if (resource?.type !== "xml" || !parseTargetArch(resource)) {
            return;
        }
        this.allLocatedOperations.set(locateOperations(this.state.resources.xml));
        this.operationsOutdated.set(false);
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
        await this.orm.call("website.assets", "reset_asset", [resource.url, resource.bundle], {
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
     * @return {Promise} indicates if the save is finished or if an error occurred.
     */
    async saveSCSSorJS(resource) {
        const { url, arch } = resource;
        const isJSFile = String(url).endsWith(".js");
        const bundle = isJSFile
            ? this.state.resources.js[url].bundle
            : this.state.resources.scss[url].bundle;
        const fileType = isJSFile ? "js" : "scss";
        const params = [url, bundle, arch, fileType];
        await this.orm.call("website.assets", "save_asset", params, { context: this.context });
        delete resource.dirty;
    }

    /**
     * Saves a unique XML view.
     *
     * @param {Object} resource an xml view to save
     * @returns {Promise} indicates if the save is finished or if an error occurred.
     */
    async saveXML(resource) {
        const { id, arch } = resource;
        await rpc("/website/save_xml", {
            view_id: id,
            arch: arch,
        });
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
        const el = this.editorRef();
        if (!el) {
            // Possibly destroyed.
            return;
        }
        const resourceId = this.state.currentResource.id;
        const error = this.errors.find(({ resource }) => resource.id === resourceId)?.error;
        if (error) {
            const { line, message } = error;
            const gutterCell = el.querySelectorAll(".ace_gutter-cell")[line - 1];
            if (gutterCell && !gutterCell.classList.contains("o_error")) {
                gutterCell.classList.add("o_error");
                gutterCell.setAttribute("data-tooltip", message);
                gutterCell.setAttribute("data-tooltip-position", "left");
            }
        }
    }

    clearErrorLine() {
        const el = this.editorRef();
        if (!el) {
            // Possibly destroyed.
            return;
        }
        const allGutterCells = el.querySelectorAll(".ace_gutter-cell");
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
        if (currentResource.type === "xml") {
            this.operationsOutdated.set(true);
            this.debouncedUpdateLocatedOperations();
        }
    }

    /**
     * Open a view on the line containing an operation
     *
     * @param {number} viewId
     * @param {number} [operationIndex=0] see `parseTargetArch`
     */
    openView(viewId, operationIndex = 0) {
        const view = this.state.resources.xml[viewId];
        this.openViewOnRow(view, getOperationRows(view)?.[operationIndex]);
    }

    /**
     * Open the view changed by an operation of the current view, on the
     * line target of the operation.
     *
     * @param {Object} target an item of `outgoingOperations`
     */
    goToTarget({ targetId, operation }) {
        const targetView = this.state.resources.xml[targetId];
        const rows = getOperationTargetRows(targetView, [operation]);
        this.openViewOnRow(targetView, rows?.[0]);
    }

    /**
     * @param {Object} view
     * @param {number|null|undefined} row the row to reveal, if known
     */
    openViewOnRow(view, row) {
        this.operationsPopover.close();
        this.state.currentResource = view;
        if (typeof row === "number") {
            this.revealRow.set({ sessionId: view.id, row });
        }
    }

    /**
     * Handle the click on gutter markers.
     *
     * Show a popover containing a list of views modifying the current line (if
     * any), followed by a list of views modified by the current line (if any).
     * If the current line only modifies a single view, directly redirect there
     * on click.
     *
     * @param {number} row
     * @param {HTMLElement} cellEl the gutter cell of the row
     */
    onMarkerClick(row, cellEl) {
        const rowIncoming = this.incomingOperations().filter((item) => item.targetRow === row);
        const rowOutgoing = this.outgoingOperations().filter((item) => item.operationRow === row);
        if (!rowIncoming.length && rowOutgoing.length === 1) {
            this.goToTarget(rowOutgoing[0]);
            return;
        }
        if (!rowIncoming.length && !rowOutgoing.length) {
            return;
        }
        const toLineNumber = (row) => (typeof row === "number" ? row + 1 : undefined);
        // Sort by view name, then by row
        const compareItems = (a, b) =>
            a.view.name.localeCompare(b.view.name) || (a.row ?? Infinity) - (b.row ?? Infinity);
        this.operationsPopover.open(cellEl, {
            row: row + 1,
            modifiedBy: rowIncoming
                .map((item) => ({
                    view: item.view,
                    row: toLineNumber(getOperationRows(item.view)?.[item.index]),
                    onSelect: () => this.openView(item.view.id, item.index),
                }))
                .sort(compareItems),
            modifies: rowOutgoing
                .map((target) => {
                    const targetView = this.state.resources.xml[target.targetId];
                    return {
                        view: targetView,
                        row: toLineNumber(
                            getOperationTargetRows(targetView, [target.operation])?.[0]
                        ),
                        onSelect: () => this.goToTarget(target),
                    };
                })
                .sort(compareItems),
        });
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

    /**
     * @param {Object|null} aceEditor
     */
    onEditorReady(aceEditor) {
        this.aceEditor = aceEditor;
    }

    openSearch() {
        this.aceEditor?.execCommand("find");
    }

    onFormat() {
        if (this.state.type === "xml") {
            const { isValid, error } = checkXML(this.state.currentResource.arch);
            if (isValid) {
                const formattedArch = formatXML(this.state.currentResource.arch);
                if (formattedArch !== this.state.currentResource.arch) {
                    this.onEditorChange(formattedArch);
                }
            } else {
                this.errors.push({ error, resource: this.state.currentResource });
            }
        }
    }

    onReset() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Reset to default?"),
            body: _t("All your custom changes will be lost. Are you sure?"),
            confirmLabel: _t("Reset"),
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
