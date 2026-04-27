/** @odoo-module */

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { SearchModel } from "@web/search/search_model";
import { GROUPABLE_TYPES } from "@web/search/utils/misc";
import {
    computeXpath,
    getNodesFromXpath,
    getNodeAttributes,
    parseStringToXml,
    serializeXmlToString,
} from "@web_studio/client_action/view_editor/editors/xml_utils";
import { EventBus, markRaw, useEnv, reactive, toRaw } from "@odoo/owl";
import { user } from "@web/core/user";
import { sprintf } from "@web/core/utils/strings";
import { parseXML } from "@web/core/utils/xml";
import { viewTypeToString } from "@web_studio/studio_service";
import {
    xpathToLegacyXpathInfo,
    cleanClickedElements,
} from "@web_studio/client_action/view_editor/editors/utils";
import { Reactive, getFieldsInArch, memoizeOnce } from "@web_studio/client_action/utils";
import { getModifier, resetViewCompilerCache } from "@web/views/view_compiler";
import { _t } from "@web/core/l10n/translation";
import { EditorOperations, SnackbarIndicator } from "@web_studio/client_action/editor/edition_flow";
import { Race } from "@web/core/utils/concurrency";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const editorsRegistry = registry.category("studio_editors");
const viewRegistry = registry.category("views");

class EditorOperationsWithSnackbar extends EditorOperations {
    constructor(params) {
        super(...arguments);
        this.snackBar = params.snackBar;
        this.race = markRaw(new Race());
    }

    _wrapPromise(prom) {
        const _prom = super._wrapPromise(prom);
        this.snackBar.add(this.race.add(_prom));
        return _prom;
    }
}

/**
 * Determines whether a given x2m field has a subview corresponding to archTag.
 * it returns hasArch, true if there is one usable arch already
 * and position, an index, starting at 1, to locate the node via an xpath
 * If there is no arch, hasArch is false, and we expect to go through "createInlineView"
 * The position is then the position of the future arch node
 */
function getSubarchPosition(mainArch, xpathToField, archTag) {
    // get eligible arch nodes, which were not automatically inlined by the server
    const xpathToArch = `${xpathToField}/${archTag}[not(@studio_subview_inlined)]`;
    const nodes = getNodesFromXpath(xpathToArch, parseStringToXml(mainArch));
    let hasArch = false;
    let position = 1;
    for (const node of nodes) {
        // When a subarch has groups="somegroup" and the user doesn't have those groups
        // The server makes it invisible via the modifiers.
        if (getModifier(node, "invisible") !== "True" && getModifier(node, "invisible") !== "1") {
            hasArch = true;
            break;
        }
        position++;
    }
    return { hasArch, position };
}

/**
 * Returns the arch of the subview
 *
 * @param {String} mainArch
 * @param {String} xpathToField
 * @param {String} viewType
 * @param {Number} position
 */
function getSubArch(mainArch, xpathToField, archTag, position) {
    const xpathToView = `${archTag}[${position}]`;
    const xpathToArch = `${xpathToField}/${xpathToView}`;
    const nodes = getNodesFromXpath(xpathToArch, parseStringToXml(mainArch));
    if (nodes.length !== 1) {
        throw new Error(`Single sub-view arch not found for xpath: ${xpathToArch}`);
    }
    return serializeXmlToString(nodes[0]);
}

function buildKey(...args) {
    return args.join("_");
}

export class ViewEditorModel extends Reactive {
    constructor({ env, services, editionFlow, viewRef, initialState = {} }) {
        super();
        this.initialState = initialState;
        this._isInEdition = false;
        this.mode = "interactive";
        this.env = env;
        this.bus = markRaw(new EventBus());
        this._services = markRaw(services);
        this._studio = services.studio;

        this._snackBar = new SnackbarIndicator();
        this._operations = new EditorOperationsWithSnackbar({
            do: this._handleOperations.bind(this),
            onDone: this._handleDone.bind(this),
            onError: this._handleError.bind(this),
            snackBar: this._snackBar,
        });

        this._decorateCall = async (callback, ...args) => {
            this._services.ui.block();
            const prom = callback(...args);
            this._snackBar.add(prom);
            try {
                return await prom;
            } finally {
                this._services.ui.unblock();
            }
        };
        this._decorateFunction = (callback) => {
            return async (...args) => {
                return this._decorateCall(callback, ...args);
            };
        };

        this._decoratedRpc = this._decorateFunction(rpc);

        this._editionFlow = editionFlow;

        this.GROUPABLE_TYPES = [...GROUPABLE_TYPES];

        this._activeNodeXpath = undefined;
        this.lastActiveNodeXpath = undefined;

        this._getEditor = memoizeOnce(() => {
            let viewType = this.viewType;
            const view = viewRegistry.contains(viewType) ? viewRegistry.get(viewType) : null;
            //FIXME remove as soon as the legacy api is removed (post v18)
            if (viewType === "kanban" && !this.mainArch.includes('t-name="card"')) {
                viewType = "kanban_legacy";
            }
            const editor = editorsRegistry.contains(viewType)
                ? editorsRegistry.get(viewType)
                : null;

            // When the mode is interactive, the priority is to get the taylor-made editor if it exists.
            // otherwise, the priority is to get the view, if it exists (e.g.:, the search editor doesn't have a view)
            return {
                getProps: editor ? editor.props : view.props,
                editor: this.mode === "interactive" ? editor || view : view || editor,
            };
        });

        this._getControllerProps = memoizeOnce(function () {
            let { resId, resIds } = this.isEditingSubview
                ? this._subviewInfo
                : this._studio.editedControllerState || {};
            resIds = resIds || [];
            resId = resId || resIds[0];

            const arch = parseXML(this.arch);
            if (this.mode !== "interactive") {
                arch.querySelectorAll(`[studio_no_fetch="1"]`).forEach((n) => n.remove());
            }

            const rootArchNode = this.xmlDoc.firstElementChild;
            const controllerClasses = Array.from(
                new Set([
                    "o_view_controller",
                    `o_${this.viewType}_view`,
                    ...(rootArchNode.getAttribute("class") || "").split(" "),
                ])
            ).filter((c) => c);

            let controllerProps = {
                info: {},
                relatedModels: { ...toRaw(this.viewDescriptions.relatedModels) },
                useSampleModel: ["graph", "pivot"].includes(this.viewType),
                searchMenuTypes: [],
                className: controllerClasses.join(" "),
                resId,
                resIds,
                resModel: this.resModel,
                arch,
                fields: { ...toRaw(this.fields) },
            };

            if (
                ["list", "list", "form"].includes(this.viewType) &&
                this.mode === "interactive" &&
                this._subviewInfo
            ) {
                controllerProps.parentRecord = this._subviewInfo.parentRecord;
            }
            // if (custom_view_id) {
            //     // for dashboard
            //     controllerProps.info.customViewId = custom_view_id;
            // }

            const { editor, getProps } = this.editorInfo;
            controllerProps = getProps
                ? getProps(controllerProps, editor, this.env.config)
                : controllerProps;

            return markRaw(controllerProps);
        });

        this.__getDefaultStudioViewProps = memoizeOnce(() => {
            const editedAction = this._studio.editedAction;
            let globalState;
            if (this._views.search && !this.isEditingSubview) {
                globalState = editedAction.globalState;
            }

            const context = this._subviewInfo ? this._subviewInfo.context : editedAction.context;
            const searchModel = this.editorInfo.editor.SearchModel || SearchModel;
            return {
                context: { ...context, studio: 1 },
                domain: editedAction.domain,
                resModel: this.resModel,
                SearchModel: searchModel,
                setOverlay:
                    !["form", "list", "list", "kanban", "search"].includes(this.viewType) ||
                    this.mode !== "interactive",
                display: { controlPanel: false, searchPanel: false },
                globalState,
            };
        });

        this._getActiveNode = memoizeOnce(() => {
            if (!this.activeNodeXpath) {
                return undefined;
            }

            const node = getNodesFromXpath(this.activeNodeXpath, this.xmlDoc)[0];
            if (!node) {
                return null;
            }
            const isField = node.tagName === "field";
            const attrs = getNodeAttributes(node);
            const humanName =
                this.editorInfo.editor.Sidebar.viewStructures?.[node.tagName]?.name || node.tagName;

            let field;
            if (isField) {
                field = reactive(this.fields[attrs.name]);
                Object.defineProperty(field, "label", {
                    get() {
                        return field.string;
                    },
                    configurable: true,
                });
            }
            return reactive({
                arch: node,
                attrs,
                humanName,
                xpath: this.activeNodeXpath,
                field,
            });
        });

        this._getUnprocessedXmlDoc = memoizeOnce((arch) => parseStringToXml(arch));

        this.breadcrumbs = editionFlow.breadcrumbs;

        this._editionFlow = editionFlow;

        this._views = {};

        this.studioViewArch = "";
        this.viewDescriptions = {
            relatedModels: {},
            fields: [],
        };
        this.viewRef = viewRef;

        this.showInvisible = initialState.showInvisible || false;

        // Keep track of the current sidebarTab to be able to
        // restore it when switching back from the xml editor
        // to the interactive editor.
        this._currentSidebarTab = undefined;

        this._getFieldsAllowedRename = memoizeOnce(() => {
            return new Set();
        });
    }

    //-----------------------------------------------------------------
    // Public getters and setters
    //-----------------------------------------------------------------
    get editorInfo() {
        return this._getEditor(buildKey(this.viewType, this.mode));
    }

    get controllerProps() {
        const key = buildKey(
            this.arch,
            this.viewType,
            this.mode,
            this.resModel,
            this.breadcrumbs.length > 1 ? this.breadcrumbs.length : 1
        );
        return this._getControllerProps(key);
    }

    get studioViewProps() {
        const key = buildKey(this.viewType, this.resModel, this.mode, this.isEditingSubview);
        return this.__getDefaultStudioViewProps(key);
    }

    get xmlDoc() {
        return this._getUnprocessedXmlDoc(this.arch);
    }

    get isEditingSubview() {
        return this.breadcrumbs.length > 1;
    }

    set isInEdition(value) {
        value = !!value; // enforce boolean
        if (this.isInEdition === value) {
            return;
        }
        this._isInEdition = value;
        if (value) {
            this._services.ui.block();
        } else {
            this._services.ui.unblock();
        }
    }

    get isInEdition() {
        return this._isInEdition;
    }

    get mainView() {
        return this._views ? this._views[this.mainViewType] : undefined;
    }

    get mainArch() {
        return this.mainView ? this.mainView.arch : "";
    }

    get mainViewType() {
        return this._studio.editedViewType;
    }

    get mainResModel() {
        return this._studio.editedAction.res_model;
    }

    get arch() {
        return this.isEditingSubview ? this._subviewInfo.getArch(this.mainArch) : this.mainArch;
    }

    get viewType() {
        return this.isEditingSubview ? this._subviewInfo.viewType : this.mainViewType;
    }

    get view() {
        return this._views[this.viewType];
    }

    get resModel() {
        return this.isEditingSubview ? this._subviewInfo.resModel : this.mainResModel;
    }

    get fields() {
        return this.viewDescriptions.relatedModels[this.resModel].fields;
    }

    get activeNode() {
        return this._getActiveNode(buildKey(this.activeNodeXpath, this.arch));
    }

    get studioViewKey() {
        return buildKey(this.arch, JSON.stringify(this.fields));
    }

    get fieldsInArch() {
        return getFieldsInArch(this.xmlDoc);
    }

    get isChatterAllowed() {
        return !this.isEditingSubview && this._isChatterAllowed;
    }

    get activeNodeXpath() {
        return this._activeNodeXpath;
    }

    set activeNodeXpath(value) {
        this._activeNodeXpath = value;
        if (value) {
            this.lastActiveNodeXpath = value;
        }
    }

    get sidebarTab() {
        if (this.activeNodeXpath) {
            return "properties";
        }
        return this._currentSidebarTab;
    }

    set sidebarTab(newTab) {
        this._currentSidebarTab = newTab;
    }

    //-----------------------------------------------------------------
    // Public methods
    //-----------------------------------------------------------------

    async editX2ManyView({ viewType, fieldName, record, xpath, fieldContext }) {
        const staticList = record.data[fieldName];
        const resIds = staticList.records.map((r) => r.resId).filter((id) => !!id);
        const resModel = staticList.resModel;
        const archTag = viewType;

        // currentFullXpath is the absolute xpath to the current edited subview as a function of the whole full arch
        // while xpath is the absolute xpath to the field we want to edit a subarch for, as a function of its subArch
        // currentFullXpath: /form[x]/field[y]/form[z]
        // xpath: /form[g]/field[h]/form[i]
        // Where form[z] and form[g] do point to the same subArch
        // We need to combine them to get a xpath of the field's arch we want to edit as a function of the entire main arch
        // what we want: /form[x]/field[y]/form[z]/field[h]/form[i]
        const currentFullXpath = this.getSubviewXpath();
        let xpathToField = xpath;
        if (currentFullXpath) {
            const xpathWithoutView = xpath.split("/").slice(2);
            xpathToField = `${currentFullXpath}/${xpathWithoutView.join("/")}`;
        }

        const { hasArch, position } = getSubarchPosition(this.mainArch, xpathToField, archTag);
        if (!hasArch) {
            const subViewRef = fieldContext[`${archTag}_view_ref`] || null;
            this.studioViewArch = await this._createInlineView({
                subViewType: viewType,
                fullXpath: xpathToField,
                subViewRef,
                resModel,
                fieldName,
            });
            const viewDescriptions = await this._editionFlow.loadViews();
            this.viewDescriptions = viewDescriptions;
            Object.assign(this._views, viewDescriptions.views);
            this._operations.clear(false);
        }
        await this._decorateCall(() => this.fieldsGet(resModel));

        const context = Object.fromEntries(
            Object.entries(fieldContext).filter(([key, val]) => {
                return !key.startsWith("default_") && !key.endsWith("_view_ref");
            })
        );

        const x2ManyEditionInfo = {
            name: sprintf("Subview %s", viewTypeToString(viewType)),
            context,
            resModel,
            resId: resIds[0],
            resIds,
            viewType,
            parentRecord: record,
            xpath: `${xpath}/${archTag}[${position}]`, // /form[x]/field[y]/list[z]
            fieldName,
            getArch: memoizeOnce((mainArch) => {
                return getSubArch(mainArch, xpathToField, archTag, position);
            }),
        };
        this._editionFlow.pushBreadcrumb(x2ManyEditionInfo);
    }

    async fieldsGet(resModel) {
        this.fieldsGetCache = this.fieldsGetCache || new Set();
        if (!this.fieldsGetCache.has(resModel)) {
            const fg = await this._services.orm.call(resModel, "fields_get");
            this.fieldsGetCache.add(resModel);
            Object.assign(this.viewDescriptions.relatedModels[resModel].fields, fg);
        }
    }

    async load() {
        const proms = [this._editionFlow.loadViews({ forceSearch: true })];

        if (this.viewType === "form") {
            proms.push(this._studio.isAllowed("chatter", this.mainResModel));
        }

        const [viewDescriptions, isChatterAllowed] = await Promise.all(proms);
        this._isChatterAllowed = isChatterAllowed;
        this.viewDescriptions = viewDescriptions || {
            relatedModels: {},
            fields: [],
        };
        Object.assign(this._views, viewDescriptions.views);
        const { mainViewId, viewId, arch } = await this._getStudioViewArch();
        this.studioViewArch = arch;
        this.studioViewId = viewId;
        if (!this.mainView.id) {
            // the call to getStudioViewArch has created the view in DB (before that, it was the default_view)
            // Clear the caches, in particular the one of the viewService to aknowledge that.
            this.env.bus.trigger("CLEAR-CACHES");
            this.mainView.id = mainViewId;
        }
    }

    getSubviewXpath() {
        if (!this.isEditingSubview) {
            return null;
        }
        const temp = [`/${this.mainViewType}[1]`];
        this.breadcrumbs.slice(1).forEach(({ data }) => {
            const withoutView = data.xpath.split("/").slice(2);
            temp.push(...withoutView);
        });
        return temp.join("/");
    }

    getFullTarget(xpath, { isXpathFullAbsolute = true } = {}) {
        const nodes = getNodesFromXpath(xpath, this.xmlDoc);
        if (nodes.length !== 1) {
            throw new Error("Xpath resolved to nothing or multiple nodes");
        }
        const element = nodes[0];

        // Attributes that could be used to identify the node python side, it is mandatory
        // Although it might be more robust to rely solely on a sufficiently expressive xpath
        const attrs = {};
        ["name", "id", "class", "for"].forEach((attrName) => {
            if (element.hasAttribute(attrName)) {
                attrs[attrName] = element.getAttribute(attrName);
            }
        });

        let xpath_info;
        if (isXpathFullAbsolute) {
            xpath_info = xpathToLegacyXpathInfo(xpath);
        } else {
            const fullAbsolute = computeXpath(element, this.viewType);
            xpath_info = xpathToLegacyXpathInfo(fullAbsolute);
        }

        const target = {
            tag: element.tagName,
            attrs,
            xpath_info,
        };

        const subViewXpath = this.getSubviewXpath();
        if (subViewXpath) {
            target.subview_xpath = subViewXpath;

            const subViewTargetInfo = xpathToLegacyXpathInfo(subViewXpath);
            xpath_info.splice(0, 1, subViewTargetInfo[subViewTargetInfo.length - 1]);
        }
        return target;
    }

    async doOperation(operation, write = true) {
        return this._operations.do(operation, !write);
    }

    pushOperation(operation) {
        return this._operations.pushOp(operation);
    }

    /** Mode and Sidebar */
    resetSidebar(tab = null) {
        this.sidebarTab = tab;
        // store the last active xpath in this variable
        this.activeNodeXpath = undefined;

        const resetEl = this.viewRef.el;
        if (resetEl) {
            cleanClickedElements(resetEl);
        }
    }

    switchMode() {
        resetViewCompilerCache();
        this.mode = this.mode === "interactive" ? "xml" : "interactive";
    }

    /** Field Renaming */
    setRenameableField(fieldName, add = true) {
        if (add) {
            this._fieldsAllowedRename.add(fieldName);
        } else {
            this._fieldsAllowedRename.delete(fieldName);
        }
    }

    isFieldRenameable(fieldName) {
        return this._fieldsAllowedRename.has(fieldName);
    }

    async renameField(fieldName, newName, { label, autoUnique = true } = {}) {
        // Sanitization
        newName = newName
            .toLowerCase()
            .trim()
            .replace(/[^\w\s-]/g, "") // remove non-word [a-z0-9_], non-whitespace, non-hyphen characters
            .replace(/[\s_-]+/g, "_") // swap any length of whitespace, underscore, hyphen characters with a single _
            .replace(/^-+|-+$/g, ""); // remove leading, trailing

        if (!newName.startsWith("x_studio_")) {
            newName = `x_studio_${newName}`;
        }

        const existingFields = this.fields;
        if (autoUnique) {
            const baseName = newName;
            let index = 1;
            while (newName in existingFields) {
                newName = baseName + "_" + index;
                index++;
            }
        }

        if (!autoUnique && newName in existingFields) {
            this._services.dialog.add(AlertDialog, {
                body: _t("A field with the same name already exists."),
            });
            return;
        }
        this.isInEdition = true;
        const prom = rpc("/web_studio/rename_field", {
            studio_view_id: this.studioViewId,
            studio_view_arch: this.studioViewArch,
            model: this.resModel,
            old_name: fieldName,
            new_name: newName,
            new_label: label,
        });

        this._snackBar.add(prom);

        try {
            await prom;
        } catch (e) {
            this.isInEdition = false;
            throw e;
        }

        const strOperations = JSON.stringify(this._operations.operations);
        // We only want to replace exact matches of the field name, but it can
        // be preceeded/followed by other characters, like parent.my_field or in
        // a domain like [('...', '...', my_field)] etc.
        // Note that negative lookbehind is not correctly handled in JS ...
        const chars = "[^\\w\\u007F-\\uFFFF]";
        const re = new RegExp(`(${chars}|^)${fieldName}(${chars}|$)`, "g");
        this._operations.clear();
        this.setRenameableField(fieldName, false);
        this.setRenameableField(newName, true);
        this._operations.doMulti(JSON.parse(strOperations.replace(re, `$1${newName}$2`)));
    }

    //-----------------------------------------------------------------
    // Private
    //-----------------------------------------------------------------

    async _createInlineView({ subViewType, fullXpath, subViewRef, resModel, fieldName }) {
        // We build the correct xpath if we are editing a 'sub' subview
        // Use specific view if available in context
        // We write views in the base language to make sure we do it on the source term field
        // of ir.ui.view
        const context = { ...user.context, lang: false, studio: true };
        if (subViewRef) {
            context[`${subViewType}_view_ref`] = subViewRef;
        }

        // FIXME: maybe this route should return def _return_view
        const studioViewArch = await this._decoratedRpc("/web_studio/create_inline_view", {
            model: resModel,
            view_id: this.mainView.id,
            field_name: fieldName,
            subview_type: subViewType,
            subview_xpath: fullXpath,
            context,
        });
        this.env.bus.trigger("CLEAR-CACHES");
        return studioViewArch;
    }

    /** Arch Edition */
    async _editView(operations) {
        const context = {
            ...user.context,
            ...(this._studio.editedAction.context || {}),
            lang: false,
            studio: true,
        };
        return rpc("/web_studio/edit_view", {
            view_id: this.mainView.id,
            studio_view_arch: this.studioViewArch,
            operations: operations,
            model: this.resModel,
            context,
        });
    }

    async _editViewArch(viewId, viewArch) {
        const context = {
            ...user.context,
            ...(this._studio.editedAction.context || {}),
            lang: false,
            studio: true,
        };
        const result = await rpc("/web_studio/edit_view_arch", {
            view_id: viewId,
            view_arch: viewArch,
            // We write views in the base language to make sure we do it on the source term field
            // of ir.ui.view
            context,
        });
        return result;
    }

    async _handleOperations({ mode, operations, lastOp }) {
        this.isInEdition = true;
        if (lastOp.type !== "replace_arch") {
            operations = operations.filter((op) => op.type !== "replace_arch");
            return this._editView(operations);
        } else {
            const viewId = lastOp.viewId;
            let { newArch, oldArch } = lastOp;
            if (mode === "undo") {
                const _newArch = newArch;
                newArch = oldArch;
                oldArch = _newArch;
            }
            return this._editViewArch(viewId, newArch);
        }
    }

    async restoreDefaultView(viewId) {
        const result = await this._editionFlow.restoreDefaultView(viewId, this.mainViewType);
        if (result) {
            this.viewDescriptions.relatedModels = result.models;
            this._views[this.mainViewType].arch = result.views[this.mainViewType].arch;
            this._operations.clear();
        }
    }

    _handleDone({ mode, pending, pendingUndone, result }) {
        this.env.bus.trigger("CLEAR-CACHES");
        if (this.mainViewType === "kanban") {
            // the cache is on a by-template basis
            // kanban may have multiple t-name templates
            // Wipe everything to force re-compilation
            resetViewCompilerCache();
        }
        if (result) {
            this.viewDescriptions.relatedModels = result.models;

            const oldArch = this._views[this.mainViewType].arch;
            const newArch = result.views[this.mainViewType].arch;
            this._views[this.mainViewType].arch = newArch;
            if (oldArch === newArch) {
                this.isInEdition = false;
            }

            if (!this.studioViewId && result.studio_view_id) {
                this.studioViewId = result.studio_view_id;
            }
        }

        const isUndoing = mode === "undo";
        const pendingOps = isUndoing ? pendingUndone : pending;
        const lastOperation = pendingOps[pendingOps.length - 1];
        if (lastOperation && lastOperation.type === "replace_arch") {
            if (lastOperation.viewId === this.studioViewId) {
                this.studioViewArch = isUndoing ? lastOperation.oldArch : lastOperation.newArch;
                this._operations.clear();
                const ops = isUndoing ? this._operations.undone : this._operations.operations;
                ops.push(lastOperation);
            }
        }
    }

    async _handleError({ mode, pending, error }) {
        this.isInEdition = false;
        this._services.notification.add(
            _t("This operation caused an error, probably because a xpath was broken"),
            {
                type: "danger",
                title: _t("Error"),
            }
        );

        Promise.resolve().then(() => {
            throw error;
        });

        this.resetSidebar("view");
        this.bus.trigger("error");
    }

    async _getStudioViewArch() {
        const result = await rpc("/web_studio/get_studio_view_arch", {
            model: this.resModel,
            view_type: this.viewType,
            view_id: this.mainView.id,
            context: { ...user.context, lang: false },
        });
        return {
            arch: result.studio_view_arch,
            viewId: result.studio_view_id,
            mainViewId: result.main_view_id,
        };
    }

    get _subviewInfo() {
        if (!this.isEditingSubview) {
            return null;
        }
        const length = this.breadcrumbs.length;
        return this.breadcrumbs[length - 1].data;
    }

    get _fieldsAllowedRename() {
        return this._getFieldsAllowedRename(
            this.breadcrumbs.length > 1 ? this.breadcrumbs.length : 1
        );
    }
}

export function useEditNodeAttributes({ isRoot = false } = {}) {
    const vem = useEnv().viewEditorModel;
    function editNodeAttributes(newAttributes) {
        let target;
        let node;
        if (isRoot) {
            target = vem.getFullTarget(`/${vem.viewType}`);
            target.isSubviewAttr = true;
        } else {
            target = vem.getFullTarget(vem.activeNodeXpath);
            const { arch, attrs } = vem.activeNode;
            node = {
                tag: arch.tagName,
                attrs,
            };
        }

        const operation = {
            new_attrs: newAttributes,
            type: "attributes",
            position: "attributes",
            target,
        };
        if (node) {
            operation.node = node;
        }
        return vem.doOperation(operation);
    }
    return editNodeAttributes;
}
