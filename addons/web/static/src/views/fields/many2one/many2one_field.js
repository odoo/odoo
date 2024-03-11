/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { Dialog } from "@web/core/dialog/dialog";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useChildRef, useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { escape, sprintf } from "@web/core/utils/strings";
import { Many2XAutocomplete, useOpenMany2XRecord } from "@web/views/fields/relational_utils";
import * as BarcodeScanner from "@web/webclient/barcode/barcode_scanner";
import { standardFieldProps } from "../standard_field_props";

import { Component, onWillUpdateProps, useState, markup } from "@odoo/owl";

class CreateConfirmationDialog extends Component {
    get title() {
        return sprintf(this.env._t("New: %s"), this.props.name);
    }

    get dialogContent() {
        return markup(
            sprintf(
                this.env._t("Create <strong>%s</strong> as a new %s?"),
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
CreateConfirmationDialog.components = { Dialog };
CreateConfirmationDialog.template = "web.Many2OneField.CreateConfirmationDialog";

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
                const resId = this.props.value[0];
                const fields = ["display_name"];
                const context = this.props.record.getFieldContext(this.props.name);
                const records = await this.orm.read(this.relation, [resId], fields, { context });
                await this.props.update(m2oTupleFromData(records[0]));
            },
            onClose: () => this.focusInput(),
            fieldString: this.props.string,
        });

        this.update = (value, params = {}) => {
            if (value) {
                value = m2oTupleFromData(value[0]);
            }
            this.state.isFloating = false;
            return this.props.update(value);
        };

        if (this.props.canQuickCreate) {
            this.quickCreate = (name, params = {}) => {
                if (params.triggeredOnBlur) {
                    return this.openConfirmationDialog(name);
                }
                return this.props.update([false, name]);
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

    get relation() {
        return this.props.relation || this.props.record.fields[this.props.name].relation;
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
    get classFromDecoration() {
        for (const decorationName in this.props.decorations) {
            if (this.props.decorations[decorationName]) {
                return `text-${decorationName}`;
            }
        }
        return "";
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
    get value() {
        return this.props.record.data[this.props.name];
    }
    get Many2XAutocompleteProps() {
        return {
            value: this.displayName,
            id: this.props.id,
            placeholder: this.props.placeholder,
            resModel: this.relation,
            autoSelect: true,
            fieldString: this.props.string,
            activeActions: this.state.activeActions,
            update: this.update,
            quickCreate: this.quickCreate,
            context: this.context,
            getDomain: this.getDomain.bind(this),
            nameCreateField: this.props.nameCreateField,
            setInputFloats: this.setFloating,
            autocomplete_container: this.autocompleteContainerRef,
            kanbanViewId: this.props.kanbanViewId,
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
                name: this.props.string,
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
        if (this.props.openTarget === "current" && !this.env.inDialog) {
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

Many2OneField.SEARCH_MORE_LIMIT = 320;

Many2OneField.template = "web.Many2OneField";
Many2OneField.components = {
    Many2XAutocomplete,
};
Many2OneField.props = {
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
    openTarget: { type: String, validate: (v) => ["current", "new"].includes(v), optional: true },
    kanbanViewId: { type: [Number, Boolean], optional: true },
};
Many2OneField.defaultProps = {
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

Many2OneField.displayName = _lt("Many2one");
Many2OneField.supportedTypes = ["many2one"];

Many2OneField.extractProps = ({ attrs, field }) => {
    const hasCreatePermission = attrs.can_create ? Boolean(JSON.parse(attrs.can_create)) : true;
    const hasWritePermission = attrs.can_write ? Boolean(JSON.parse(attrs.can_write)) : true;

    const noOpen = Boolean(attrs.options.no_open);
    const noCreate = Boolean(attrs.options.no_create);
    const canCreate = hasCreatePermission && !noCreate;
    const canWrite = hasWritePermission;
    const noQuickCreate = Boolean(attrs.options.no_quick_create);
    const noCreateEdit = Boolean(attrs.options.no_create_edit);
    const canScanBarcode = Boolean(attrs.options.can_scan_barcode);

    return {
        placeholder: attrs.placeholder,
        canOpen: !noOpen,
        canCreate,
        canWrite,
        canQuickCreate: canCreate && !noQuickCreate,
        canCreateEdit: canCreate && !noCreateEdit,
        relation: field.relation,
        string: attrs.string || field.string,
        nameCreateField: attrs.options.create_name_field,
        canScanBarcode: canScanBarcode,
        openTarget: attrs.open_target,
        kanbanViewId: attrs.kanban_view_ref ? JSON.parse(attrs.kanban_view_ref) : false,
    };
};

registry.category("fields").add("many2one", Many2OneField);
// the two following lines are there to prevent the fallback on legacy widgets
registry.category("fields").add("list.many2one", Many2OneField);
registry.category("fields").add("kanban.many2one", Many2OneField);
