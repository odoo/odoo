odoo.define("web.DataExport", function (require) {
    "use strict";

    const config = require("web.config");
    const Dialog = require("web.Dialog");
    const data = require("web.data");
    const framework = require("web.framework");
    const OwlDialog = require("web.OwlDialog");
    const pyUtils = require("web.py_utils");

    const { useRef, useState } = owl.hooks;

    //--------------------------------------------------------------------------
    // Utility functions
    //--------------------------------------------------------------------------
    /*
     * Adds class on given collection of element
     * @param {HTMLElement | NodeList | Object[]} element
     * @param {string} className
     */
    function addClass(elements, className) {
        elements = elements instanceof HTMLElement ? [elements] : elements;
        return elements && elements.forEach((el) => el && el.classList.add(className));
    }

    /*
     * Hides given collection of element
     * @param {HTMLElement | NodeList | Object[]} element
     */
    function hide(elements) {
        addClass(elements, "d-none");
    }

    /**
     * @param {HTMLElement | NodeList | Object[]} node
     * @param {String} selector
     * @returns {HTMLElement}
     */
    function nextElement(node, selector) {
        node = node.nextElementSibling;
        for (; node && node !== document; node = node.nextElementSibling) {
            if (node.matches(selector)) {
                return node;
            }
        }
        return null;
    }

    /**
     * @param {HTMLElement | NodeList | Object[]} node
     * @param {String} selector
     * @returns {HTMLElement}
     */
    function parent(node, selector) {
        node = node.parentNode;
        for (; node && node !== document; node = node.parentNode) {
            if (node.matches(selector)) {
                return node;
            }
        }
        return null;
    }

    /**
     * @param {HTMLElement | NodeList | Object[]} node
     * @param {String} selector
     * @returns {HTMLElement[]}
     */
    function parents(node, selector) {
        let current = node,
            list = [];
        while (current.parentNode !== null && current.parentNode !== document.documentElement) {
            if (current.parentNode.matches(selector)) {
                list.push(current.parentNode);
            }
            current = current.parentNode;
        }
        return list;
    }

    /**
     * @param {HTMLElement | NodeList | Object[]} node
     * @param {String} selector
     * @returns {HTMLElement}
     */
    function previousElement(node, selector) {
        node = node.previousElementSibling;
        for (; node && node !== document; node = node.previousElementSibling) {
            if (node.matches(selector)) {
                return node;
            }
        }
        return null;
    }

    /**
     *
     * @param {HTMLElement | NodeList | Object[]} node
     * @param {String} selector
     * @returns {HTMLElement[]}
     */
    function prevAll(node, selector) {
        let list = [];
        let prevSibling = node.previousElementSibling;
        while (prevSibling) {
            if (prevSibling.matches(selector)) {
                list.push(prevSibling);
            }
            prevSibling = prevSibling.previousElementSibling;
        }
        return list;
    }

    /*
     * Removes class on given collection of element
     * @param {HTMLElement | NodeList | Object[]} element
     * @param {string} className
     */
    function removeClass(elements, className) {
        elements = elements instanceof HTMLElement ? [elements] : elements;
        return elements && elements.forEach((el) => el && el.classList.remove(className));
    }

    /*
     * Displays given collection of element
     * @param {HTMLElement | NodeList | Object[]} element
     */
    function show(elements) {
        removeClass(elements, "d-none");
    }

    /**
     * Toggles class based on give condition on give elements
     *
     * @param {HTMLElement | NodeList | Object[]} elements
     * @param {String} className class to toggle
     * @param {Boolean} condition true/false
     */
    function toggleClass(elements, className, condition) {
        elements = elements instanceof HTMLElement ? [elements] : elements;
        return (
            elements &&
            elements.forEach((el) => {
                if (condition && !el.classList.contains(className)) {
                    el.classList.add(className);
                } else {
                    el.classList.remove(className);
                }
            })
        );
    }

    class DataExport extends owl.Component {
        /**
         * @constructor
         * @param {Widget} parent
         * @param {Object} props
         * @param {string[]} props.defaultExportFields
         */
        constructor(parent, props) {
            super(...arguments);
            this.records = {};
            this.record = props.record;
            this.defaultExportFields = props.defaultExportFields;
            this.groupby = props.groupedBy;
            this.exports = new data.DataSetSearch(this, "ir.exports", this.record.getContext());
            this.rowIndex = 0;
            this.rowIndexLevel = 0;
            this.isCompatibleMode = false;
            this.domain = props.activeDomain || this.record.domain;
            this.idsToExport = props.activeDomain ? false : props.idsToExport;

            this.exportDialog = useRef("exportDialog");
            this.state = useState({ exportedList: [] });
        }
        /**
         * @override
         */
        mounted() {
            const self = this;
            const proms = [super.mounted(...arguments)];
            this.dialog = this.exportDialog.comp.modalRef.el;

            // The default for the ".modal_content" element is "max-height: 100%;"
            // but we want it to always expand to "height: 100%;" for this modal.
            // This can be achieved thanks to CSS modification without touching
            // the ".modal-content" rules... but not with Internet explorer (11).
            this.dialog.querySelector(".modal-content").style.height = "100%";

            this.fieldsList = this.dialog.querySelector(".o_fields_list");

            proms.push(
                this.env.services.rpc({ route: "/web/export/formats" }).then(doSetupExportFormats)
            );
            proms.push(
                this._onChangeCompatibleInput().then(() => {
                    self.defaultExportFields.forEach((field) => {
                        const record = self.records[field];
                        this._addField(record.id, record.string);
                    });
                })
            );

            proms.push(this._showExportsList());

            // Bind sortable events after Dialog is open
            $(this.dialog.querySelector(".o_fields_list")).sortable({
                axis: "y",
                handle: ".o_short_field",
                forcePlaceholderSize: true,
                placeholder: "o-field-placeholder",
                update: self._resetTemplateField.bind(this),
            });

            function doSetupExportFormats(formats) {
                const fmts = self.dialog.querySelector(".o_export_format");

                formats.forEach(function (format) {
                    const radio = document.createElement("input");
                    radio.setAttribute("type", "radio");
                    radio.setAttribute("value", format.tag);
                    radio.setAttribute("name", "o_export_format_name");
                    radio.setAttribute("class", "form-check-input");
                    radio.setAttribute("id", "o_radio" + format.label);

                    const label = document.createElement("label");
                    label.innerHTML = format.label;
                    label.setAttribute("class", "form-check-label");
                    label.setAttribute("for", "o_radio" + format.label);

                    if (format.error) {
                        radio.disabled = true;
                        label.innerHTML = `${format.label} — ${format.error}`;
                    }

                    const div = document.createElement("div");
                    div.setAttribute("class", "radio form-check form-check-inline pl-4");
                    div.appendChild(radio);
                    div.appendChild(label);
                    fmts.appendChild(div);
                });

                self.exportFormatInputs = fmts.querySelectorAll("input");
                const filtedFormatInputs = [...self.exportFormatInputs].filter((input) => {
                    return !input.disabled;
                });
                filtedFormatInputs[0].checked = true;
            }
            return Promise.all(proms);
        }

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * Export all data with default values (fields, domain)
         */
        export() {
            let exportedFields = this.defaultExportFields.map((field) => ({
                name: field,
                label: this.record.fields[field].string,
            }));
            this._exportData(exportedFields, "xlsx", false);
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Add the field in the export list
         *
         * @private
         * @param {string} fieldID
         * @param {string} label
         */
        _addField(fieldID, label) {
            var fieldList = this.dialog.querySelector(".o_fields_list");
            if (!fieldList.querySelector(".o_export_field[data-field_id='" + fieldID + "']")) {
                const li = document.createElement("li");
                li.setAttribute("class", "o_export_field");
                li.setAttribute("data-field_id", fieldID);
                const span = document.createElement("span");
                span.setAttribute("class", "fa fa-arrows o_short_field mx-1");
                li.appendChild(span);
                li.appendChild(document.createTextNode(label.trim()));
                const spanRemove = document.createElement("span");
                spanRemove.setAttribute("class", "fa fa-trash m-1 pull-right o_remove_field");
                spanRemove.setAttribute("title", this.env._t("Remove field"));
                li.appendChild(spanRemove);
                fieldList.appendChild(li);
                spanRemove.addEventListener("click", this._onClickRemoveField.bind(this));
            }
        }
        /**
         * @private
         */
        _addNewTemplate() {
            this.dialog.querySelector(".o_exported_lists").classList.add("d-none");

            const saveList = this.dialog.querySelector(".o_save_list");
            show(saveList);
            const saveListName = saveList.querySelector(".o_save_list_name");
            saveListName.value = "";
            saveListName.focus();
        }
        /**
         * Submit the user data and export the file
         *
         * @private
         */
        _exportData(exportedFields, exportFormat, idsToExport) {
            if (!Object.entries(exportedFields).length) {
                Dialog.alert(this, this.env._t("Please select fields to export..."));
                return;
            }
            if (this.isCompatibleMode) {
                exportedFields.unshift({ name: "id", label: this.env._t("External ID") });
            }

            framework.blockUI();
            this.env.session.get_file({
                url: "/web/export/" + exportFormat,
                data: {
                    data: JSON.stringify({
                        model: this.record.model,
                        fields: exportedFields,
                        ids: idsToExport,
                        domain: this.domain,
                        groupby: this.groupby,
                        context: pyUtils.eval("contexts", [this.record.getContext()]),
                        import_compat: this.isCompatibleMode,
                    }),
                },
                complete: framework.unblockUI,
                error: (error) => this.call("crash_manager", "rpc_error", error),
            });
        }
        /**
         * @private
         * @returns {string[]} exportFields
         */
        _getFields() {
            const exportFields = [...this.dialog.querySelectorAll(".o_export_field")].map((el) => {
                return el.getAttribute("data-field_id");
            });
            if (exportFields.length === 0) {
                Dialog.alert(this, this.env._t("Please select fields to save export list..."));
            }
            return exportFields;
        }
        /**
         * Fetch the field info for the relational field. This method will be
         * invoked when the user expands the relational field from keyboard/mouse.
         *
         * @private
         * @param {Object} record
         */
        async _onExpandAction(record) {
            if (!record.children) {
                return;
            }

            const model = record.params.model;
            const prefix = record.params.prefix;
            const name = record.params.name;
            const excludeFields = [];
            if (record.relation_field) {
                excludeFields.push(record.relation_field);
            }

            if (!record.loaded) {
                const results = await this.env.services.rpc({
                    route: "/web/export/get_fields",
                    params: {
                        model: model,
                        prefix: prefix,
                        parent_name: name,
                        import_compat: this.isCompatibleMode,
                        parent_field_type: record.field_type,
                        parent_field: record.params.parent_field,
                        exclude: excludeFields,
                    },
                });
                record.loaded = true;
                this._onShowData(results, record.id);
            } else {
                this._showContent(record.id);
            }
        }
        /**
         * After the fetching the fields info for the relational field, this method
         * will render a list of a field for expanded relational field.
         *
         * @private
         * @param {Object[]} records
         * @param {string} expansion
         */
        _onShowData(records, expansion) {
            const leftFieldPanel = this.dialog.querySelector(".o_left_field_panel");
            let exportTreeItemEl;
            if (expansion) {
                const exportTreeItem = this.dialog.querySelector(
                    '.o_export_tree_item[data-id="' + expansion + '"]'
                );
                exportTreeItem.classList.add("show");
                const expandParent = exportTreeItem.querySelector(".o_expand_parent");
                expandParent.classList.toggle("fa-chevron-right");
                expandParent.classList.toggle("fa-chevron-down");
                expandParent.parentElement.innerHTML += this.env.qweb.renderToString(
                    "Export.TreeItems",
                    {
                        fields: records,
                        debug: config.isDebug(),
                    }
                );
                exportTreeItemEl = exportTreeItem.querySelector(".o_export_tree_items");
            } else {
                // make leftFieldPanel empty
                leftFieldPanel.innerHTML = "";
                const div = document.createElement("div");
                div.setAttribute("class", "o_field_tree_structure");
                div.innerHTML = this.env.qweb.renderToString("Export.TreeItems", {
                    fields: records,
                    debug: config.isDebug(),
                });
                leftFieldPanel.appendChild(div);
                exportTreeItemEl = div;
            }

            const recordsObject = records.reduce((obj, item) => {
                return Object.assign(obj, { [item["id"]]: item });
            }, {});
            Object.assign(this.records, recordsObject);
            this.recordElements = this.dialog.querySelectorAll(".o_export_tree_item");
            this.recordElements.forEach((el) => {
                const treeColumn = el.querySelector(".o_tree_column");
                this.records[el.getAttribute("data-id")].required
                    ? treeColumn.classList.add("o_required")
                    : treeColumn.classList.remove("o_required");
            });
            this.dialog.querySelector("#o-export-search-filter").value = "";
            // Bind events to Tree Items
            [...exportTreeItemEl.querySelectorAll(".o_add_field")].map((field) => {
                field.addEventListener("click", this._onClickAddField.bind(this));
            });
            [...exportTreeItemEl.querySelectorAll(".o_expand")].map((field) => {
                field.addEventListener("click", this._onClickExpand.bind(this));
            });
            [...exportTreeItemEl.querySelectorAll(".o_export_tree_item")].map((item) => {
                item.addEventListener("click", this._onClickTreeItem.bind(this));
                item.addEventListener("keydown", this._onKeydownTreeItem.bind(this));
            });
            [...exportTreeItemEl.querySelectorAll(".o_export_tree_item:not(.haschild)")].map(
                (item) => {
                    item.addEventListener("dblclick", this._onDblclickTreeItem.bind(this));
                }
            );
        }
        /**
         * @private
         */
        _resetTemplateField() {
            const exportedListSelect = this.dialog.querySelector(".o_exported_lists_select");
            if (exportedListSelect) {
                exportedListSelect.value = "";
            }
            const deleteExportedList = this.dialog.querySelector(".o_delete_exported_list");
            if (deleteExportedList) {
                deleteExportedList.classList.add("d-none");
            }
            this.dialog.querySelector(".o_exported_lists").classList.remove("d-none");

            hide(this.dialog.querySelector(".o_save_list"));
            this.dialog.querySelector(".o_save_list .o_save_list_name").value = "";
        }
        /**
         * If relational fields info is already fetched then this method is
         * used to display fields.
         *
         * @private
         * @param {string} fieldID
         */
        _showContent(fieldID) {
            const item = this.dialog.querySelector(
                '.o_export_tree_item[data-id="' + fieldID + '"]'
            );
            item.classList.toggle("show");
            const isOpen = item.classList.contains("show");

            const itemExpandParent = [...item.children].filter((el) => {
                return el.matches(".o_expand_parent") && el;
            });
            toggleClass(itemExpandParent, "fa-chevron-down", isOpen);
            toggleClass(itemExpandParent, "fa-chevron-right", !isOpen);

            const childField = item.querySelectorAll(".o_export_tree_item");
            const childLength = fieldID.split("/").length + 1;
            for (let i = 0; i < childField.length; i++) {
                const child = childField[i];
                if (!isOpen) {
                    hide(child);
                } else if (
                    childLength === childField[i].getAttribute("data-id").split("/").length
                ) {
                    if (child.classList.contains("show")) {
                        child.classList.remove("show");
                        const childExpandParents = [...child.children].filter((el) => {
                            return el.matches(".o_expand_parent") && el;
                        });
                        removeClass(childExpandParents, "fa-chevron-down");
                        addClass(childExpandParents, "fa-chevron-right");
                    }
                    show(child);
                }
            }
            this.dialog.querySelector("#o-export-search-filter").value = "";
        }
        /**
         * Fetches the saved export list for the current model
         *
         * @private
         * @returns {Deferred}
         */
        async _showExportsList() {
            if (
                this.dialog.querySelector(".o_exported_lists_select") &&
                this.dialog.querySelector(".o_exported_lists_select").style.display === "none"
            ) {
                show(this.dialog.querySelector(".o_exported_lists"));
                return Promise.resolve();
            }

            const exportList = await this.env.services.rpc({
                model: "ir.exports",
                method: "search_read",
                fields: ["name"],
                domain: [["resource", "=", this.record.model]],
            });
            this.state.exportedList = exportList;
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @returns {Deferred}
         */
        async _onChangeCompatibleInput() {
            this.isCompatibleMode =
                this.dialog.querySelector(".o_import_compat input").checked === true;

            const treeStructure = this.dialog.querySelector(".o_field_tree_structure");
            if (treeStructure) {
                treeStructure.parentNode.removeChild(treeStructure);
            }
            this._resetTemplateField();
            const records = await this.env.services.rpc({
                route: "/web/export/get_fields",
                params: {
                    model: this.record.model,
                    import_compat: this.isCompatibleMode,
                },
            });
            const compatibleFields = records.map((record) => {
                return record.id;
            });
            this._onShowData(records);
            const fieldList = this.dialog.querySelector(".o_fields_list");
            // make fieldlist empty
            fieldList.innerHTML = "";

            let fields = [...this.fieldsList.querySelectorAll(".o_export_field")].map((field) => {
                return field.getAttribute("data-field_id");
            });
            fields = [...new Set([...fields, ...this.defaultExportFields])];
            fields = fields.filter((field) => compatibleFields.includes(field));
            fields.forEach((field) => {
                const record = records.find((rec) => {
                    return rec.id === field;
                });
                this._addField(record.id, record.string);
            });
            this.dialog.querySelector("#o-export-search-filter").value = "";
        }
        /**
         * This method will fill fields to export when user change exported field list
         *
         * @private
         */
        async _onChangeExportList() {
            const exportedListSelect = this.dialog.querySelector(".o_exported_lists_select");
            const exportID = exportedListSelect.options[exportedListSelect.selectedIndex].value;
            const deleteExportList = this.dialog.querySelector(".o_delete_exported_list");
            !exportID
                ? deleteExportList.classList.add("d-none")
                : deleteExportList.classList.remove("d-none");
            if (exportID && exportID !== "new_template") {
                const fieldListElem = this.dialog.querySelector(".o_fields_list");
                // make fieldListElem empty
                fieldListElem.innerHTML = "";
                const fieldList = await this.env.services.rpc({
                    route: "/web/export/namelist",
                    params: {
                        model: this.record.model,
                        export_id: parseInt(exportID, 10),
                    },
                });
                fieldList.forEach((field) => {
                    this._addField(field.name, field.label);
                });
            } else if (exportID === "new_template") {
                this._addNewTemplate();
            }
        }
        /**
         * Add a field to export list
         *
         * @private
         * @param {Event} ev
         */
        _onClickAddField(ev) {
            ev.stopPropagation();
            const field = ev.currentTarget;
            this._resetTemplateField();
            this._addField(
                field.closest(".o_export_tree_item").getAttribute("data-id"),
                field.closest(".o_tree_column").innerText
            );
        }
        /**
         * Delete selected export list item from the saved export list
         *
         * @private
         */
        _onClickDeleteExportListBtn() {
            const exportSelect = this.dialog.querySelector(".o_exported_lists_select");
            const selectExp = exportSelect.options[exportSelect.selectedIndex];
            var options = {
                confirm_callback: () => {
                    if (selectExp.value) {
                        this.exports.unlink([parseInt(selectExp.value, 10)]);
                        selectExp.remove();
                        if (
                            this.dialog.querySelectorAll(".o_exported_lists_select option")
                                .length <= 1
                        ) {
                            hide(this.dialog.querySelector(".o_exported_lists"));
                        }
                    }
                },
            };
            Dialog.confirm(
                this,
                this.env._t("Do you really want to delete this export template?"),
                options
            );
        }
        /**
         * @private
         * @param {Event} ev
         */
        _onClickExpand(ev) {
            this._onExpandAction(
                this.records[ev.target.closest(".o_export_tree_item").getAttribute("data-id")]
            );
        }
        /**
         * Remove selected field from export field list
         *
         * @private
         * @param {Event} ev
         */
        _onClickRemoveField(ev) {
            ev.currentTarget.closest(".o_export_field").remove();
            this._resetTemplateField();
        }
        /**
         * This method will create a record in 'ir.exports' model with list of
         * selected fields.
         *
         * @private
         */
        async _onClickSaveListBtn() {
            const saveList = this.dialog.querySelector(".o_save_list");

            const value = saveList.querySelector("input").value;
            if (!value) {
                Dialog.alert(this, this.env._t("Please enter save field list name"));
                return;
            }

            const fields = this._getFields();
            if (fields.length === 0) {
                return;
            }

            hide(saveList);

            const exportListID = await this.exports.create({
                name: value,
                resource: this.record.model,
                export_fields: fields.map((field) => {
                    return [0, 0, { name: field }];
                }),
            });
            if (!exportListID) {
                return;
            }
            const select = this.dialog.querySelector(".o_exported_lists_select");
            if (select || select.style.display === "none") {
                this._showExportsList();
            }
            select.appendChild(new Option(value, exportListID));
            this.dialog.querySelector(".o_exported_lists").classList.remove("d-none");
            select.value = exportListID;
        }
        /**
         * @private
         * @param ev
         */
        _onClickTreeItem(ev) {
            ev.stopPropagation();
            const elem = ev.currentTarget;

            const rowIndex = prevAll(elem, ".o_export_tree_item").length;
            const rowIndexLevel = parents(elem, ".o_export_tree_item").length;

            if (ev.shiftKey && rowIndexLevel === this.rowIndexLevel) {
                const minIndex = Math.min(rowIndex, this.rowIndex);
                const maxIndex = Math.max(rowIndex, this.rowIndex);

                const filteredRecordElements = [...this.recordElements].filter((el) => {
                    return elem.parentElement === el.parentElement;
                });
                let slicedRecordElements = filteredRecordElements.slice(minIndex, maxIndex + 1);
                addClass(slicedRecordElements, "o_selected");
                slicedRecordElements.splice(-1, 1).forEach((elem) => processChildren(elem));
            }

            this.rowIndex = rowIndex;
            this.rowIndexLevel = rowIndexLevel;

            if (ev.ctrlKey) {
                elem.classList.toggle("o_selected");
                elem.focus();
            } else if (ev.shiftKey) {
                elem.classList.add("o_selected");
                elem.focus();
            } else {
                removeClass(this.dialog.querySelectorAll(".o_selected"), "o_selected");
                elem.classList.add("o_selected");
                elem.focus();
            }

            function processChildren(elem) {
                const child = elem;
                if (child.classList.contains("show")) {
                    const exportTreeItems = [...child.children].filter((el) => {
                        return el.matches(".o_export_tree_item") && el;
                    });
                    exportTreeItems.map((el) => {
                        elem.classList.add("o_selected");
                        processChildren(elem);
                    });
                }
            }
        }
        /**
         * Closes dialog
         *
         * @private
         */
        _onCloseDialog() {
            this.destroy();
        }
        /**
         * Add a field to export field list on double click
         *
         * @private
         * @param {Event} ev
         */
        _onDblclickTreeItem(ev) {
            this._resetTemplateField();
            const addElement = (el) => {
                this._addField(
                    el.getAttribute("data-id"),
                    el.querySelector(".o_tree_column").textContent
                );
            };
            const target = ev.currentTarget;
            target.classList.remove("o_selected");
            // Add parent fields to export
            [].reverse.call(parents(target, ".o_export_tree_item")).forEach((element) => {
                addElement(element);
            });
            // add field itself
            addElement(target);
        }
        /**
         * Submit the user data and export the file
         *
         * @private
         */
        _onExportData() {
            const exportedFields = [...this.dialog.querySelectorAll(".o_export_field")].map(
                (field) => ({
                    name: field.getAttribute("data-field_id"),
                    label: field.textContent,
                })
            );
            const exportFormat = [...this.exportFormatInputs].find((format) => {
                return format.checked === true;
            }).value;
            this._exportData(exportedFields, exportFormat, this.idsToExport);
        }
        /**
         * @private
         * @param ev
         */
        _onKeydownSaveList(ev) {
            if (ev.keyCode === $.ui.keyCode.ENTER) {
                this._onClickSaveListBtn();
            }
        }
        /**
         * Handles the keyboard navigation for the fields
         *
         * @private
         * @param ev
         */
        _onKeydownTreeItem(ev) {
            ev.stopPropagation();
            const el = ev.currentTarget;
            const record = this.records[el.getAttribute("data-id")];

            switch (ev.keyCode || ev.which) {
                case $.ui.keyCode.LEFT:
                    if (el.classList.contains("show")) {
                        this._onExpandAction(record);
                    }
                    break;
                case $.ui.keyCode.RIGHT:
                    if (!el.classList.contains("show")) {
                        this._onExpandAction(record);
                    }
                    break;
                case $.ui.keyCode.UP:
                    var prev = previousElement(el, ".o_export_tree_item"); 
                    if (prev) {
                        // if previous element has child and is opened then select last element of it
                        while (prev && prev.classList.contains("show")) {
                            const prevExportItems = [...prev.children].filter((el) => {
                                return el.matches(".o_export_tree_items") && el;
                            }).slice(-1).pop();
                            prev = [...prevExportItems.children].filter((el) => {
                                return el.matches(".o_export_tree_item") && el;
                            }).slice(-1).pop();
                        }
                    } else {
                        prev = parent(el, ".o_export_tree_item");
                        if (!prev) {
                            break;
                        }
                    }

                    el.classList.remove("o_selected");
                    el.blur();
                    prev.classList.add("o_selected");
                    prev.focus();
                    break;
                case $.ui.keyCode.DOWN:
                    var next;
                    if (el.classList.contains("show")) {
                        const nextExportItems = [...el.children].filter((el) => {
                            return el.matches(".o_export_tree_items") && el;
                        }).slice(0, 1).pop();
                        next = [...nextExportItems.children].filter((el) => {
                            return el.matches(".o_export_tree_item") && el;
                        }).slice(0, 1).pop();
                    } else {
                        next = nextElement(el, ".o_export_tree_item");
                        if (!next) {
                            const parentElement = parent(el, ".o_export_tree_item");
                            next = nextElement(parentElement, ".o_export_tree_item");
                            if (!next) {
                                break;
                            }
                        }
                    }

                    el.classList.remove("o_selected");
                    el.blur();
                    next.classList.add("o_selected");
                    next.focus();
                    break;
            }
        }
        /**
         * Search fields from a field list.
         *
         * @private
         */
        _onSearchInput(ev) {
            const searchText = ev.currentTarget.value.trim().toUpperCase();
            if (!searchText) {
                if (this.dialog.querySelector(".o_no_match")) {
                    this.dialog.querySelector(".o_no_match").remove();
                }
                show(this.dialog.querySelectorAll(".o_export_tree_item"));
                hide(
                    this.dialog.querySelectorAll(
                        ".o_export_tree_item.haschild:not(.show) .o_export_tree_item"
                    )
                );
                return;
            }

            const matchItems = [...this.dialog.querySelectorAll(".o_tree_column")]
                .filter((column) => {
                    const title = column.getAttribute("title");
                    return (
                        column.innerText.toUpperCase().indexOf(searchText) >= 0 ||
                        (title && title.toUpperCase().indexOf(searchText) >= 0)
                    );
                })
                .map((column) => {
                    return column.parentNode;
                });
            hide(this.dialog.querySelectorAll(".o_export_tree_item"));
            if (matchItems.length) {
                if (this.dialog.querySelector(".o_no_match")) {
                    this.dialog.querySelector(".o_no_match").remove();
                }
                matchItems.forEach((col) => {
                    show(col);
                    const parentElements = parents(col, ".haschild.show");
                    show(parentElements);
                    if (
                        !col.parentElement.parentElement.classList.contains("show") &&
                        !col.parentElement.parentElement.classList.contains(
                            "o_field_tree_structure"
                        )
                    ) {
                        hide(col);
                    }
                });
            } else if (!this.dialog.querySelector(".o_no_match")) {
                const h3 = document.createElement("h3");
                h3.setAttribute("class", "text-center text-muted mt-5 o_no_match");
                h3.appendChild(document.createTextNode(this.env._t("No match found.")));
                this.dialog.querySelector(".o_field_tree_structure").appendChild(h3);
            }
        }
    }

    DataExport.template = "ExportDialog";
    DataExport.components = { Dialog: OwlDialog };

    return DataExport;
});
