import { Component, onWillRender, reactive, toRaw, useEffect, useRef, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { Time } from "@web/core/l10n/time";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { parseXML } from "@web/core/utils/xml";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { CallbackRecorder, useSetupAction } from "@web/search/action_hook";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { MultiCreatePopover } from "./multi_create_popover";

export class MultiSelectionButtons extends Component {
    static template = "web.MultiSelectionButtons";
    static props = { reactive: Object };

    setup() {
        this.viewService = useService("view");
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

        this.multiCreatePopover = usePopover(MultiCreatePopover, {
            onClose: () => {
                const multiCreateData = this.getMultiCreateDataFromPopover();
                if (multiCreateData) {
                    this.storeMultiCreateData(multiCreateData);
                }
            },
        });
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
            () => [rootRef.el]
        );

        useHotkey("escape", () => {
            if (this.props.reactive.visible) {
                this.props.reactive.onCancel();
            }
        });
    }

    getMultiCreateDataFromPopover() {
        const fn = this.callbackRecorder.callbacks[0];
        return fn?.() || null;
    }

    storeMultiCreateData(multiCreateData) {
        this.storeTimeRange(multiCreateData.timeRange);
        this.multiCreateValues = this.computeValues(multiCreateData.record);
    }

    async loadMultiCreateView() {
        // todo: accept variable context,... ?
        const { context, resModel, multiCreateView } = this.props.reactive;
        const { fields, relatedModels, views } = await this.viewService.loadViews({
            context: { ...context, form_view_ref: multiCreateView },
            resModel,
            views: [[false, "form"]],
        });
        const parser = new FormArchParser();
        const arch = views.form.arch;
        this.multiCreateArchInfo = parser.parse(parseXML(arch), relatedModels, resModel);
        const { activeFields } = extractFieldsFromArchInfo(this.multiCreateArchInfo, fields);
        this.multiCreateRecordProps = { resModel, fields, activeFields, context };
    }

    getMultiCreatePopoverProps() {
        return {
            timeRange: this.props.reactive.showMultiCreateTimeRange ? this.getTimeRange() : null,
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

    getTimeRange() {
        return {
            start: new Time(this.getItemFromStorage("timeRange_start", { hour: 12, minute: 0 })),
            end: new Time(this.getItemFromStorage("timeRange_end", { hour: 13, minute: 0 })),
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
        browser.localStorage.setItem(this.generateLocalStorageKey(key), JSON.stringify(value));
    }

    storeTimeRange(timeRange) {
        if (timeRange?.start) {
            this.setItemInStorage("timeRange_start", timeRange.start);
        }
        if (timeRange?.end) {
            this.setItemInStorage("timeRange_end", timeRange.end);
        }
    }

    computeValues(record) {
        const multiCreateFormRecord = toRaw(record);
        const values = Object.assign({}, multiCreateFormRecord.data);
        for (const [fieldName, data] of Object.entries(multiCreateFormRecord.data)) {
            if (["one2many", "many2many"].includes(multiCreateFormRecord.fields[fieldName].type)) {
                values[fieldName] = data.records.map((record) =>
                    Object.assign({ id: record.resId }, record.data)
                );
            }
        }
        return values;
    }

    onAdd() {
        if (this.multiCreatePopover.isOpen) {
            return;
        }
        this.multiCreatePopover.open(this.addButtonRef.el, this.getMultiCreatePopoverProps());
    }
}

/**
 * @param {Object} params
 * @param {Function} params.onAdd
 * @param {Function} params.onCancel
 * @param {Function} params.onDelete
 * @param {number} params.nbSelected
 * @param {string} params.multiCreateView
 * @param {string} params.resModel
 * @param {Object} [params.multiCreateValues]
 * @param {boolean} [params.showMultiCreateTimeRange=false]
 * @param {boolean} [params.visible=false]
 * @param {Object} [params.context={}]
 * @returns {Object}
 */
export function useMultiSelectionButtons({
    onAdd,
    onCancel,
    onDelete,
    nbSelected,
    multiCreateView,
    resModel,
    multiCreateValues,
    showMultiCreateTimeRange,
    visible,
    context,
}) {
    return reactive({
        onCancel,
        onAdd,
        onDelete,
        nbSelected,
        multiCreateView,
        resModel,
        multiCreateValues,
        visible: Boolean(visible),
        showMultiCreateTimeRange: Boolean(showMultiCreateTimeRange),
        context: context || {},
    });
}
