/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { makeContext } from "@web/core/context";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { useChildRef, useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { Many2XAutocomplete, useOpenMany2XRecord } from "@web/views/fields/relational_utils";
import * as BarcodeScanner from "@web/webclient/barcode/barcode_scanner";
import { standardFieldProps } from "../standard_field_props";

import { Component, onWillUpdateProps, useState, markup } from "@odoo/owl";

class CreateConfirmationDialog extends Component {
    static template = "web.Many2OneField.CreateConfirmationDialog";
    static components = { Dialog };

    get title() {
        return _t("New: %s", this.props.name);
    }

    get dialogContent() {
        return markup(
            _t(
                "Create <strong>%s</strong> as a new %s?",
                escape(this.props.value),
                escape(this.props.name)
            )
        );
    }

    async onCreate() {
        await this.props.create();
        this.props.close();
    }
}

export function m2oTupleFromData(data) {
    const id = data.id;
    let name;
    if ("display_name" in data) {
        name = data.display_name;
    } else {
        const _name = data.name;
        name = Array.isArray(_name) ? _name[1] : _name;
    }
    return [id, name];
}

export class Many2OneField extends Component {
    static template = "web.Many2OneField";
    static components = {
        Many2XAutocomplete,
    };
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        canOpen: { type: Boolean, optional: true },
        canCreate: { type: Boolean, optional: true },
        canWrite: { type: Boolean, optional: true },
        canQuickCreate: { type: Boolean, optional: true },
        canCreateEdit: { type: Boolean, optional: true },
        context: { type: String, optional: true },
        domain: { type: [Array, Function], optional: true },
        nameCreateField: { type: String, optional: true },
        searchLimit: { type: Number, optional: true },
        relation: { type: String, optional: true },
        string: { type: String, optional: true },
        canScanBarcode: { type: Boolean, optional: true },
        update: { type: Function, optional: true },
        value: { optional: true },
        decorations: { type: Object, optional: true },
    };
    static defaultProps = {
        canOpen: true,
        canCreate: true,
        canWrite: true,
        canQuickCreate: true,
        canCreateEdit: true,
        nameCreateField: "name",
        searchLimit: 7,
        string: "",
        canScanBarcode: false,
        context: {},
        decorations: {},
    };

    static SEARCH_MORE_LIMIT = 320;

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.autocompleteContainerRef = useChildRef();
        this.addDialog = useOwnedDialogs();

        this.focusInput = () => {
            this.autocompleteContainerRef.el.querySelector("input").focus();
        };

        this.state = useState({
            isFloating: false,
        });
        this.computeActiveActions(this.props);

        this.openMany2X = useOpenMany2XRecord({
            resModel: this.relation,
            activeActions: this.state.activeActions,
            isToMany: false,
            onRecordSaved: async (record) => {
                const resId = this.value[0];
                const fields = ["display_name"];
                // use unity read + relatedFields from Field Component
                const records = await this.orm.read(this.relation, [resId], fields, {
                    context: this.context,
                });
                await this.updateRecord(m2oTupleFromData(records[0]));
            },
            onClose: () => this.focusInput(),
            fieldString: this.string,
        });

        this.update = (value, params = {}) => {
            if (value) {
                value = m2oTupleFromData(value[0]);
            }
            this.state.isFloating = false;
            return this.updateRecord(value);
        };

        if (this.props.canQuickCreate) {
            this.quickCreate = (name, params = {}) => {
                if (params.triggeredOnBlur) {
                    return this.openConfirmationDialog(name);
                }
                this.state.isFloating = false;
                return this.updateRecord([false, name]);
            };
        }

        this.setFloating = (bool) => {
            this.state.isFloating = bool;
        };

        onWillUpdateProps(async (nextProps) => {
            this.computeActiveActions(nextProps);
        });
    }

    updateRecord(value) {
        const changes = { [this.props.name]: value };
        if (this.props.update) {
            return this.props.update(changes);
        }
        return this.props.record.update(changes);
    }

    get relation() {
        return this.props.relation || this.props.record.fields[this.props.name].relation;
    }
    get string() {
        return this.props.string || this.props.record.fields[this.props.name].string || "";
    }
    get hasExternalButton() {
        return this.props.canOpen && !!this.value && !this.state.isFloating;
    }
    get context() {
        const { context, record } = this.props;
        const evalContext = record.getEvalContext
            ? record.getEvalContext(false)
            : record.evalContext;
        return makeContext([context], evalContext);
    }
    get classFromDecoration() {
        const evalContext = this.props.record.evalContextWithVirtualIds;
        for (const decorationName in this.props.decorations) {
            if (evaluateBooleanExpr(this.props.decorations[decorationName], evalContext)) {
                return `text-${decorationName}`;
            }
        }
        return "";
    }
    get displayName() {
        if (this.value && this.value[1]) {
            return this.value[1].split("\n")[0];
        } else if (this.value) {
            return _t("Unnamed");
        } else {
            return "";
        }
    }
    get extraLines() {
        return this.value && this.value[1]
            ? this.value[1]
                  .split("\n")
                  .map((line) => line.trim())
                  .slice(1)
            : [];
    }
    get resId() {
        return this.value && this.value[0];
    }
    get value() {
        return "value" in this.props ? this.props.value : this.props.record.data[this.props.name];
    }
    get Many2XAutocompleteProps() {
        return {
            value: this.displayName,
            id: this.props.id,
            placeholder: this.props.placeholder,
            resModel: this.relation,
            autoSelect: true,
            fieldString: this.string,
            activeActions: this.state.activeActions,
            update: this.update,
            quickCreate: this.quickCreate,
            context: this.context,
            getDomain: this.getDomain.bind(this),
            nameCreateField: this.props.nameCreateField,
            setInputFloats: this.setFloating,
            autocomplete_container: this.autocompleteContainerRef,
        };
    }
    computeActiveActions(props) {
        this.state.activeActions = {
            create: props.canCreate,
            createEdit: props.canCreateEdit,
            write: props.canWrite,
        };
    }
    getDomain() {
        let domain = this.props.domain;
        if (typeof domain === "function") {
            domain = domain();
        }
        return domain;
    }
    async openAction() {
        const action = await this.orm.call(this.relation, "get_formview_action", [[this.resId]], {
            context: this.context,
        });
        await this.action.doAction(action);
    }
    async openDialog(resId) {
        return this.openMany2X({ resId, context: this.context });
    }

    async openConfirmationDialog(request) {
        return new Promise((resolve, reject) => {
            this.addDialog(CreateConfirmationDialog, {
                value: request,
                name: this.string,
                create: async () => {
                    try {
                        await this.quickCreate(request);
                        resolve();
                    } catch (e) {
                        reject(e);
                    }
                },
            });
        });
    }

    onClick(ev) {
        if (this.props.canOpen && this.props.readonly) {
            ev.stopPropagation();
            this.openAction();
        }
    }
    onExternalBtnClick() {
        if (this.env.inDialog) {
            this.openDialog(this.resId);
        } else {
            this.openAction();
        }
    }
    async onBarcodeBtnClick() {
        const barcode = await BarcodeScanner.scanBarcode(this.env);
        if (barcode) {
            await this.onBarcodeScanned(barcode);
            if ("vibrate" in browser.navigator) {
                browser.navigator.vibrate(100);
            }
        } else {
            this.notification.add(_t("Please, scan again!"), {
                type: "warning",
            });
        }
    }
    async search(barcode) {
        const results = await this.orm.call(this.relation, "name_search", [], {
            name: barcode,
            args: this.getDomain(),
            operator: "ilike",
            limit: 2, // If one result we set directly and if more than one we use normal flow so no need to search more
            context: this.context,
        });
        return results.map((result) => {
            const [id, displayName] = result;
            return {
                id,
                name: displayName,
            };
        });
    }
    async onBarcodeScanned(barcode) {
        const results = await this.search(barcode);
        const records = results.filter((r) => !!r.id);
        if (records.length === 1) {
            this.update([{ id: records[0].id, name: records[0].name }]);
        } else {
            const searchInput = this.autocompleteContainerRef.el.querySelector("input");
            searchInput.value = barcode;
            searchInput.dispatchEvent(new Event("input"));
            if (this.env.isSmall) {
                searchInput.dispatchEvent(new Event("barcode-search"));
            }
        }
    }
    get hasBarcodeButton() {
        const canScanBarcode = this.props.canScanBarcode;
        const supported = BarcodeScanner.isBarcodeScannerSupported();
        return canScanBarcode && isMobileOS() && supported && !this.hasExternalButton;
    }
}

export const many2OneField = {
    component: Many2OneField,
    displayName: _t("Many2one"),
    supportedOptions: [
        {
            label: _t("Disable opening"),
            name: "no_open",
            type: "boolean",
        },
        {
            label: _t("Disable creation"),
            name: "no_create",
            type: "boolean",
            help: _t(
                "If checked, users won't be able to create records through the autocomplete dropdown at all."
            ),
        },
        {
            label: _t("Disable 'Create' option"),
            name: "no_quick_create",
            type: "boolean",
            help: _t(
                "If checked, users will not be able to create records based on the text input; they will still be able to create records via a popup form."
            ),
        },
        {
            label: _t("Disable 'Create and Edit' option"),
            name: "no_create_edit",
            type: "boolean",
            help: _t(
                "If checked, users will not be able to create records based through a popup form; they will still be able to create records based on the text input."
            ),
        },
    ],
    supportedTypes: ["many2one"],
    extractProps({ attrs, context, decorations, options, string }, dynamicInfo) {
        const hasCreatePermission = attrs.can_create ? evaluateBooleanExpr(attrs.can_create) : true;
        const hasWritePermission = attrs.can_write ? evaluateBooleanExpr(attrs.can_write) : true;
        const canCreate = options.no_create ? false : hasCreatePermission
        return {
            placeholder: attrs.placeholder,
            canOpen: !options.no_open,
            canCreate,
            canWrite: hasWritePermission,
            canQuickCreate: canCreate && !options.no_quick_create,
            canCreateEdit: canCreate && !options.no_create_edit,
            context: context,
            decorations,
            domain: dynamicInfo.domain,
            nameCreateField: options.create_name_field,
            canScanBarcode: !!options.can_scan_barcode,
            string,
        };
    },
};

registry.category("fields").add("many2one", many2OneField);
// the two following lines are there to prevent the fallback on legacy widgets
registry.category("fields").add("list.many2one", many2OneField);
registry.category("fields").add("kanban.many2one", many2OneField);
