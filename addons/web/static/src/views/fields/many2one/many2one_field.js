/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { useChildRef, useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { standardFieldProps } from "../standard_field_props";
import { Many2XAutocomplete, useOpenMany2XRecord } from "@web/views/fields/relational_utils";
import { isMobileOS } from "@web/core/browser/feature_detection";
import * as BarcodeScanner from "@web/webclient/barcode/barcode_scanner";

import { Component, onWillUpdateProps, useState } from "@odoo/owl";

class CreateConfirmationDialog extends Component {
    static template = "web.Many2OneField.CreateConfirmationDialog";
    static components = { Dialog };

    get title() {
        return sprintf(this.env._t("New: %s"), this.props.name);
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
        nameCreateField: { type: String, optional: true },
        searchLimit: { type: Number, optional: true },
        relation: { type: String, optional: true },
        string: { type: String, optional: true },
        canScanBarcode: { type: Boolean, optional: true },
        update: { type: Function, optional: true },
        openTarget: {
            type: String,
            validate: (v) => ["current", "new"].includes(v),
            optional: true,
        },
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
        openTarget: "current",
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
            isFloating: !this.props.value,
        });
        this.computeActiveActions(this.props);

        this.openMany2X = useOpenMany2XRecord({
            resModel: this.relation,
            activeActions: this.state.activeActions,
            isToMany: false,
            onRecordSaved: async (record) => {
                await this.props.record.load();
                await this.updateRecord(m2oTupleFromData(record.data));
                if (this.props.record.model.root.id !== this.props.record.id) {
                    this.props.record.switchMode("readonly");
                }
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
                return this.updateRecord([false, name]);
            };
        }

        this.setFloating = (bool) => {
            this.state.isFloating = bool;
        };

        onWillUpdateProps(async (nextProps) => {
            this.state.isFloating = !nextProps.value;
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
    get context() {
        return this.props.record.getFieldContext(this.props.name);
    }
    get domain() {
        return this.props.record.getFieldDomain(this.props.name);
    }
    get hasExternalButton() {
        return this.props.canOpen && !!this.props.value && !this.state.isFloating;
    }
    get displayName() {
        return this.props.value ? this.props.value[1].split("\n")[0] : "";
    }
    get extraLines() {
        return this.props.value
            ? this.props.value[1]
                  .split("\n")
                  .map((line) => line.trim())
                  .slice(1)
            : [];
    }
    get resId() {
        return this.props.value && this.props.value[0];
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
        return this.domain.toList(this.context);
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
        if (this.props.openTarget === "current") {
            this.openAction();
        } else {
            this.openDialog(this.resId);
        }
    }
    async onBarcodeBtnClick() {
        const barcode = await BarcodeScanner.scanBarcode();
        if (barcode) {
            await this.onBarcodeScanned(barcode);
            if ("vibrate" in browser.navigator) {
                browser.navigator.vibrate(100);
            }
        } else {
            this.notification.add(this.env._t("Please, scan again !"), {
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
    displayName: _lt("Many2one"),
    supportedTypes: ["many2one"],
    extractProps: ({ attrs }) => {
        const canCreate =
            attrs.can_create && Boolean(JSON.parse(attrs.can_create)) && !attrs.options.no_create;
        return {
            placeholder: attrs.placeholder,
            canOpen: !attrs.options.no_open,
            canCreate,
            canWrite: attrs.can_write && Boolean(JSON.parse(attrs.can_write)),
            canQuickCreate: canCreate && !attrs.options.no_quick_create,
            canCreateEdit: canCreate && !attrs.options.no_create_edit,
            nameCreateField: attrs.options.create_name_field,
            canScanBarcode: !!attrs.options.can_scan_barcode,
            openTarget: attrs.open_target,
            string: attrs.string,
        };
    },
};

registry.category("fields").add("many2one", many2OneField);
// the two following lines are there to prevent the fallback on legacy widgets
registry.category("fields").add("list.many2one", many2OneField);
registry.category("fields").add("kanban.many2one", many2OneField);
