// @ts-check

/** @module @web/views/view_components/multi_selection_buttons - Floating toolbar with Add/Cancel/Delete for multi-record selection in calendar/gantt views */

import { Component, onWillRender, toRaw, useEffect, useRef, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Time } from "@web/core/l10n/time";
import { _t } from "@web/core/l10n/translation";
import { parseXML } from "@web/core/utils/dom/xml";
import { useService } from "@web/core/utils/hooks";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { CallbackRecorder, useSetupAction } from "@web/search/action_hook";
import { useHotkey } from "@web/services/hotkeys/hotkey_hook";
import { ConfirmationDialog } from "@web/ui/dialog/confirmation_dialog";
import { usePopover } from "@web/ui/popover/popover_hook";
import { FormArchParser } from "@web/views/form/form_arch_parser";

import { MultiCreatePopover } from "./multi_create_popover";

/** Floating toolbar with Add/Cancel/Delete actions for multi-record selection in calendar/gantt views, with a multi-create popover. */
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

    setup() {
        this.viewService = useService("view");
        this.dialogService = useService("dialog");
        this.state = useState({ isReady: false });
        onWillRender(() => {
            if (this.props.reactive.visible && !this.state.isReady) {
                this.loadMultiCreateView().then(() => {
                    this.state.isReady = true;
                });
            }
        });

        this.multiCreateValues = this.props.reactive.multiCreateValues;
        this.callbackRecorder = new CallbackRecorder();
        useSetupAction({
            getLocalState: () => {
                const multiCreateData = this.getMultiCreateDataFromPopover();
                if (multiCreateData) {
                    this.storeMultiCreateData(multiCreateData);
                }
                return { multiCreateValues: this.multiCreateValues };
            },
        });

        this.multiCreatePopover = usePopover(
            /** @type {any} */ (this.constructor).components.Popover,
            {
                onClose: () => {
                    const multiCreateData = this.getMultiCreateDataFromPopover();
                    if (multiCreateData) {
                        this.storeMultiCreateData(multiCreateData);
                    }
                },
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
            () => [rootRef.el],
        );

        useHotkey("escape", () => {
            if (this.props.reactive.visible) {
                this.props.reactive.onCancel();
            }
        });
    }

    /** @returns {Object | null} current form data from the open popover, or null */
    getMultiCreateDataFromPopover() {
        const fn = this.callbackRecorder.callbacks[0];
        return fn?.() || null;
    }

    /** Persist time range to localStorage and cache form values for reuse. */
    storeMultiCreateData(multiCreateData) {
        this.storeTimeRange(multiCreateData.timeRange);
        this.multiCreateValues = this.computeValues(multiCreateData.record);
    }

    /** Fetch and parse the multi-create form view definition from the server. */
    async loadMultiCreateView() {
        // todo: accept variable context,... ?
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
        const arch = views.form.arch;
        this.multiCreateArchInfo = parser.parse(
            parseXML(arch),
            relatedModels,
            resModel,
        );
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

    /** @returns {Object} props to pass to the MultiCreatePopover component */
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

    /** @returns {{ start: Time, end: Time }} time range from localStorage or defaults */
    getTimeRange() {
        return {
            start: new Time(
                this.getItemFromStorage("timeRange_start", {
                    hour: 12,
                    minute: 0,
                }),
            ),
            end: new Time(
                this.getItemFromStorage("timeRange_end", {
                    hour: 13,
                    minute: 0,
                }),
            ),
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
     * Extract plain data values from a form record, flattening x2many sub-records.
     * @param {Object} record - ORM record proxy
     * @returns {Object} flat values dict suitable for re-creation
     */
    computeValues(record) {
        const multiCreateFormRecord = toRaw(record);
        const values = { ...multiCreateFormRecord.data };
        for (const [fieldName, data] of Object.entries(multiCreateFormRecord.data)) {
            if (
                ["one2many", "many2many"].includes(
                    multiCreateFormRecord.fields[fieldName].type,
                )
            ) {
                values[fieldName] = data.records.map((record) =>
                    Object.assign({ id: record.resId }, record.data),
                );
            }
        }
        return values;
    }

    /** Open the multi-create popover anchored to the Add button. */
    onAdd() {
        if (this.multiCreatePopover.isOpen) {
            return;
        }
        this.multiCreatePopover.open(
            this.addButtonRef.el,
            this.getMultiCreatePopoverProps(),
        );
    }

    /** Show a confirmation dialog before deleting all selected records. */
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
