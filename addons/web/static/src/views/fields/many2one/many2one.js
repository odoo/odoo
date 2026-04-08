import { Component, toRaw, useRef, useState } from "@odoo/owl";
import * as BarcodeScanner from "@web/core/barcode/barcode_dialog";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { useService } from "@web/core/utils/hooks";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { Many2XAutocomplete, useOpenMany2XRecord } from "../relational_utils";

///////////////////////////////////////////////////////////////////////////////
// UTILS
///////////////////////////////////////////////////////////////////////////////

function extractData(record) {
    let name;
    if ("display_name" in record) {
        name = record.display_name;
    } else if ("name" in record) {
        name = record.name.id ? record.name.display_name : record.name;
    }
    return { id: record.id, display_name: name };
}

export function computeM2OProps(fieldProps) {
    const computeLinkCssClass = () => {
        const evalContext = fieldProps.record.evalContextWithVirtualIds;
        for (const decorationName in fieldProps.decorations) {
            if (evaluateBooleanExpr(fieldProps.decorations[decorationName], evalContext)) {
                return `text-${decorationName}`;
            }
        }
        return "";
    };

    return {
        canCreate: fieldProps.canCreate,
        canCreateEdit: fieldProps.canCreateEdit,
        canOpen: fieldProps.canOpen,
        canQuickCreate: fieldProps.canQuickCreate,
        canScanBarcode: fieldProps.canScanBarcode,
        canWrite: fieldProps.canWrite,
        context: fieldProps.context,
        domain: () => getFieldDomain(fieldProps.record, fieldProps.name, fieldProps.domain),
        id: fieldProps.id,
        linkCssClass: computeLinkCssClass(),
        nameCreateField: fieldProps.nameCreateField,
        openActionContext: () => {
            const { context, name, openActionContext, record } = fieldProps;
            return makeContext(
                [openActionContext || context, record.fields[name].context],
                record.evalContext
            );
        },
        placeholder: fieldProps.placeholder,
        readonly: fieldProps.readonly,
        relation: fieldProps.record.fields[fieldProps.name].relation,
        searchThreshold: fieldProps.searchThreshold,
        preventMemoization: fieldProps.preventMemoization,
        string: fieldProps.string || fieldProps.record.fields[fieldProps.name].string || "",
        update: (value, options = {}) =>
            fieldProps.record.update({ [fieldProps.name]: value }, options),
        value: toRaw(fieldProps.record.data[fieldProps.name]),
    };
}

///////////////////////////////////////////////////////////////////////////////
// Components
///////////////////////////////////////////////////////////////////////////////

export class Many2One extends Component {
    static template = "web.Many2One";
    static components = { Many2XAutocomplete };
    static props = {
        canCreate: { type: Boolean, optional: true },
        canCreateEdit: { type: Boolean, optional: true },
        canOpen: { type: Boolean, optional: true },
        canQuickCreate: { type: Boolean, optional: true },
        canScanBarcode: { type: Boolean, optional: true },
        canWrite: { type: Boolean, optional: true },
        context: { type: Object, optional: true },
        createAction: { type: Function, optional: true },
        cssClass: { type: String, optional: true },
        domain: { type: Function, optional: true },
        id: { type: String, optional: true },
        linkCssClass: { type: String, optional: true },
        nameCreateField: { type: String, optional: true },
        openActionContext: { type: Function, optional: true },
        openRecordAction: { type: Function, optional: true },
        otherSources: { type: Array, optional: true },
        placeholder: { type: String, optional: true },
        readonly: { type: Boolean, optional: true },
        relation: { type: String },
        searchMoreLabel: { type: String, optional: true },
        searchThreshold: { type: Number, optional: true },
        preventMemoization: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        specification: { type: Object, optional: true },
        string: { type: String, optional: true },
        update: { type: Function },
        value: { type: [Array, Object, { value: false }], optional: true },
    };
    static defaultProps = {
        canCreate: true,
        canCreateEdit: true,
        canOpen: true,
        canQuickCreate: true,
        canScanBarcode: false,
        canWrite: true,
        context: {},
        domain: [],
        linkCssClass: "",
        nameCreateField: "name",
        otherSources: [],
        placeholder: "",
        readonly: false,
        string: "",
    };

    setup() {
        this.rootRef = useRef("root");

        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");

        this.state = useState({ isFloating: false });

        this.recordDialog = {
            open: useOpenMany2XRecord({
                activeActions: this.activeActions,
                fieldString: this.props.string,
                isToMany: false,
                onClose: () => {
                    this.input.focus();
                },
                onRecordSaved: async () => {
                    const resId = this.props.value?.id;
                    const fieldNames = ["display_name"];
                    // use unity read + relatedFields from Field Component
                    const records = await this.orm.read(this.props.relation, [resId], fieldNames, {
                        context: this.props.context,
                    });
                    await this.update(records[0] ? extractData(records[0]) : false);
                },
                onRecordDiscarded: () => {},
                resModel: this.props.relation,
            }),
        };
    }

    get activeActions() {
        return {
            create: this.props.canCreate,
            createEdit: this.props.canCreateEdit,
            write: this.props.canWrite,
        };
    }

    get many2XAutocompleteProps() {
        return {
            activeActions: this.activeActions,
            autoSelect: true,
            context: this.props.context,
            createAction: this.props.createAction,
            fieldString: this.props.string,
            getDomain: this.props.domain,
            id: this.props.id,
            nameCreateField: this.props.nameCreateField,
            otherSources: this.props.otherSources,
            placeholder: this.props.placeholder,
            quickCreate: this.props.canQuickCreate ? (name) => this.quickCreate(name) : null,
            resModel: this.props.relation,
            searchMoreLabel: this.props.searchMoreLabel,
            searchThreshold: this.props.searchThreshold,
            preventMemoization: this.props.preventMemoization,
            setInputFloats: (isFloating) => {
                this.state.isFloating = isFloating;
            },
            slots: this.props.slots,
            specification: this.props.specification,
            update: (records) => {
                const idNamePair = records && records[0] ? extractData(records[0]) : false;
                return this.update(idNamePair);
            },
            value: this.displayName,
        };
    }

    get displayName() {
        if (this.props.value) {
            if (this.props.value.display_name) {
                return this.props.value.display_name.split("\n")[0];
            } else {
                return _t("Unnamed");
            }
        } else {
            return "";
        }
    }

    get extraLines() {
        const name = this.props.value?.display_name;
        return name
            ? name
                  .split("\n")
                  .map((line) => line.trim())
                  .slice(1)
            : [];
    }

    get hasBarcodeButton() {
        const supported = isBarcodeScannerSupported();
        return this.props.canScanBarcode && isMobileOS() && supported && !this.hasLinkButton;
    }

    get hasLinkButton() {
        return this.props.canOpen && !!this.props.value && !this.state.isFloating;
    }

    get input() {
        return this.rootRef.el?.querySelector("input");
    }

    get linkHref() {
        if (!this.props.value) {
            return "/";
        }
        const relation = this.props.relation.includes(".")
            ? this.props.relation
            : `m-${this.props.relation}`;
        return `/odoo/${relation}/${this.props.value.id}`;
    }

    async openBarcodeScanner() {
        const barcode = await BarcodeScanner.scanBarcode(this.env);
        if (barcode) {
            await this.processScannedBarcode(barcode);
            if ("vibrate" in navigator) {
                navigator.vibrate(100);
            }
        } else {
            /** @type {any} */
            const message = _t("Please, scan again!");
            this.notification.add(message, { type: "warning" });
        }
    }

    async openRecord(mode) {
        if (this.props.openRecordAction) {
            return this.props.openRecordAction(mode);
        }

        switch (mode) {
            case "action": {
                return this.openRecordInAction(false);
            }
            case "dialog": {
                return this.openRecordInDialog();
            }
            case "tab": {
                return this.openRecordInAction(true);
            }
        }
    }

    async openRecordInAction(newWindow) {
        const action = await this.orm.call(
            this.props.relation,
            "get_formview_action",
            [[this.props.value?.id]],
            { context: this.props.openActionContext() }
        );
        await this.action.doAction(action, { newWindow });
    }

    async openRecordInDialog() {
        return this.recordDialog.open({
            resId: this.props.value?.id,
            context: this.props.context,
        });
    }

    async processScannedBarcode(barcode) {
        const pairs = await this.orm.call(this.props.relation, "name_search", [], {
            name: barcode,
            domain: this.props.domain(),
            operator: "ilike",
            limit: 2, // If one result we set directly and if more than one we use normal flow so no need to search more
            context: this.props.context,
        });
        const validPairs = pairs.filter(([id]) => !!id);
        if (validPairs.length === 1) {
            const pair = validPairs[0];
            return this.update({ id: pair[0], display_name: pair[1] });
        } else {
            const input = this.input;
            input.value = barcode;
            input.dispatchEvent(new Event("input"));
            if (this.env.isSmall) {
                input.dispatchEvent(new Event("barcode-search"));
            }
        }
    }

    quickCreate(name) {
        return this.update({ id: false, display_name: name });
    }

    update(idNamePair) {
        this.state.isFloating = false;
        return this.props.update(idNamePair);
    }
}

class KanbanMany2OneAssignPopover extends Many2One {
    static props = {
        ...super.props,
        close: Function,
    };

    get many2XAutocompleteProps() {
        return {
            ...super.many2XAutocompleteProps,
            dropdown: false,
        };
    }
}

export class KanbanMany2One extends Component {
    static template = "web.KanbanMany2One";
    static props = { ...Many2One.props };

    setup() {
        this.assignPopover = usePopover(KanbanMany2OneAssignPopover, {
            popoverClass: "o_m2o_tags_avatar_field_popover",
        });
    }

    openAssignPopover(target) {
        this.assignPopover.open(target, {
            ...this.props,
            canCreate: false,
            canCreateEdit: false,
            canQuickCreate: false,
            placeholder: this.props.placeholder || _t("Search user..."),
            readonly: false,
            update: async (value) => {
                await this.props.update(value, { save: true });
                this.assignPopover.close();
            },
        });
    }
}
