// @ts-check
/** @odoo-module native */

import { Component, onWillRender, toRaw, useEffect, useRef, useState } from "@odoo/owl";
import { CallbackRecorder, useSetupAction } from "@web/core/action_hook";
import { browser } from "@web/core/browser/browser";
import { reportUncaught } from "@web/core/errors/error_utils";
import { isX2ManyType } from "@web/core/field_types";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { Time } from "@web/core/l10n/time";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { extractFieldsFromArchInfo } from "@web/model/relational_model";
import { ConfirmationDialog } from "@web/ui/dialog/confirmation_dialog";
import { usePopover } from "@web/ui/popover/popover_hook";
import { FormArchParser } from "@web/views/form/form_arch_parser";

import { MultiCreatePopover } from "./multi_create_popover.js";

export class MultiSelectionButtons extends Component {
    static template = "web.MultiSelectionButtons";
    static props = {
        reactive: {
            type: Object,
            shape: {
                onAdd: Function,
                onCancel: Function,
                onDelete: Function,
                nbSelected: Number,
                multiCreateView: String,
                resModel: String,
                context: Object,
                showMultiCreateTimeRange: Boolean,
                visible: Boolean,
                multiCreateValues: { type: Object, optional: true },
            },
        },
    };
    static components = {
        Popover: MultiCreatePopover,
    };

    /** @type {import("@odoo/owl").Ref} */
    addButtonRef;
    /** @type {CallbackRecorder} */
    callbackRecorder;
    /** @type {import("services").ServiceFactories["dialog"]} */
    dialogService;
    /** @type {ReturnType<typeof usePopover>} */
    multiCreatePopover;
    /** @type {{ isReady: boolean }} */
    state;
    /** @type {import("services").ServiceFactories["view"]} */
    viewService;

    setup() {
        this.viewService = useService("view");
        this.dialogService = useService("dialog");
        this.state = useState({ isReady: false });
        onWillRender(() => {
            if (this.props.reactive.visible && !this.state.isReady) {
                this._loadViewProm ??= this.loadMultiCreateView()
                    .then(() => {
                        this.state.isReady = true;
                    })
                    .catch((error) => {
                        this._loadViewProm = null;
                        reportUncaught(error);
                    });
            }
        });

        this.multiCreateValues = this.props.reactive.multiCreateValues;
        this.callbackRecorder = new CallbackRecorder();
        useSetupAction({
            getLocalState: () => {
                this.persistPopoverData();
                return { multiCreateValues: this.multiCreateValues };
            },
        });

        this.multiCreatePopover = usePopover(
            /** @type {any} */ (this.constructor).components.Popover,
            {
                onClose: () => this.persistPopoverData(),
            },
        );
        this.addButtonRef = useRef("addButton");

        const rootRef = useRef("root");
        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                // @ts-ignore
                const { width: parentWidth } = el.parentElement.getBoundingClientRect();
                const { width } = el.getBoundingClientRect();
                const left = Math.floor((parentWidth - width) / 2);
                el.style.setProperty("left", `${left}px`);
            },
            () => [rootRef.el, this.props.reactive.nbSelected],
        );

        useHotkey("escape", () => {
            if (this.props.reactive.visible) {
                this.props.reactive.onCancel();
            }
        });
    }

    persistPopoverData() {
        const multiCreateData = this.callbackRecorder.callbacks[0]?.();
        if (multiCreateData) {
            this.storeMultiCreateData(multiCreateData);
        }
    }

    storeMultiCreateData(multiCreateData) {
        this.storeTimeRange(multiCreateData.timeRange);
        this.multiCreateValues = this.computeValues(multiCreateData.record);
    }

    async loadMultiCreateView() {
        const { context, resModel, multiCreateView } = this.props.reactive;
        const result = await this.viewService.loadViews(
            /** @type {any} */ ({
                context: { ...context, form_view_ref: multiCreateView },
                resModel,
                views: [[false, "form"]],
            }),
        );
        const { fields, relatedModels, views } = /** @type {any} */ (result);
        const parser = new FormArchParser();
        this.multiCreateArchInfo = parser.parse(views.form.ir, relatedModels, resModel);
        const { activeFields } = extractFieldsFromArchInfo(
            this.multiCreateArchInfo,
            fields,
        );
        this.multiCreateRecordProps = {
            resModel,
            fields,
            activeFields,
            context,
        };
    }

    /** @returns {Object} */
    getMultiCreatePopoverProps() {
        return {
            timeRange: this.props.reactive.showMultiCreateTimeRange
                ? this.getTimeRange()
                : null,
            multiCreateArchInfo: { ...this.multiCreateArchInfo },
            multiCreateRecordProps: {
                ...this.multiCreateRecordProps,
                values: this.multiCreateValues,
            },
            onAdd: (multiCreateData) => {
                this.storeMultiCreateData(multiCreateData);
                this.props.reactive.onAdd(multiCreateData);
            },
            callbackRecorder: this.callbackRecorder,
        };
    }

    /** @returns {{ start: Time, end: Time }} */
    getTimeRange() {
        const stored = (key, fallback) =>
            Time.from(this.getItemFromStorage(key, fallback)) ?? new Time(fallback);
        return {
            start: stored("timeRange_start", { hour: 12, minute: 0 }),
            end: stored("timeRange_end", { hour: 13, minute: 0 }),
        };
    }

    generateLocalStorageKey(key) {
        const { resModel } = this.props.reactive;
        return `multiCreate_${key}_${resModel}`;
    }

    getItemFromStorage(key, defaultValue) {
        const item = browser.localStorage.getItem(this.generateLocalStorageKey(key));
        try {
            return item ? JSON.parse(item) : defaultValue;
        } catch {
            return defaultValue;
        }
    }

    setItemInStorage(key, value) {
        browser.localStorage.setItem(
            this.generateLocalStorageKey(key),
            JSON.stringify(value),
        );
    }

    storeTimeRange(timeRange) {
        if (timeRange?.start) {
            this.setItemInStorage("timeRange_start", timeRange.start);
        }
        if (timeRange?.end) {
            this.setItemInStorage("timeRange_end", timeRange.end);
        }
    }

    /**
     * @param {Object} record
     * @returns {Object}
     */
    computeValues(record) {
        const multiCreateFormRecord = toRaw(record);
        const values = { ...multiCreateFormRecord.data };
        for (const [fieldName, data] of Object.entries(multiCreateFormRecord.data)) {
            if (isX2ManyType(multiCreateFormRecord.fields[fieldName].type)) {
                values[fieldName] = data.records.map((record) =>
                    Object.assign({ id: record.resId }, record.data),
                );
            }
        }
        return values;
    }

    onAdd() {
        if (this.multiCreatePopover.isOpen) {
            return;
        }
        this.multiCreatePopover.open(
            /** @type {HTMLElement} */ (this.addButtonRef.el),
            this.getMultiCreatePopoverProps(),
        );
    }

    onDelete() {
        const body =
            this.props.reactive.nbSelected === 1
                ? _t("Are you sure you want to delete the selected record?")
                : _t(
                      "Are you sure you want to delete the %(nbSelected)s selected records?",
                      {
                          nbSelected: this.props.reactive.nbSelected,
                      },
                  );
        this.dialogService.add(ConfirmationDialog, {
            body,
            confirm: async () => {
                this.props.reactive.onDelete();
            },
            cancel: () => {},
        });
    }
}
