/** @odoo-module **/

import options from '@web_editor/js/editor/snippets.options';

options.registry.OnlineAppointmentOptions = options.Class.extend({
    allAppointmentTypesById: {},

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    /**
     * Load available appointment types and update obsolete snippet data if necessary.
     *
     * @override
     */
    async willStart() {
        await this._super(...arguments);
        this.allAppointmentTypesById = await this.rpc('/appointment/get_snippet_data');
        // If no appointments are available as opposed to when the button was created.
        if (!Object.keys(this.allAppointmentTypesById).length) {
            this._setDatasetProperty('targetTypes', 'all');
        } else if (this._getDatasetProperty('targetTypes') !== 'all') {
            // Handle case where (some) selected appointments are no longer available
            const selectedAppointmentTypesIds = this._getDatasetProperty('appointmentTypes', true);
            const appointmentTypeIdsToKeep = selectedAppointmentTypesIds.filter(apptId => {
                return Object.prototype.hasOwnProperty.call(this.allAppointmentTypesById, apptId);
            });
            if (!appointmentTypeIdsToKeep.length) {
                this._setDatasetProperty('targetTypes', 'all');
            } else if (appointmentTypeIdsToKeep.length !== selectedAppointmentTypesIds.length) {
                this._setDatasetProperty('appointmentTypes', appointmentTypeIdsToKeep);
            } else {
                // Handle case where selected staffUsers(s) no longer available
                if (this._getDatasetProperty('targetUsers') !== 'all') {
                    const selectedUserIds = this._getDatasetProperty('staffUsers', true);
                    const availableUserIds = this.allAppointmentTypesById[selectedAppointmentTypesIds[0]].staff_users
                        .map(u => u.id);
                    const userIdsToKeep = selectedUserIds.filter(uid => availableUserIds.includes(uid));
                    if (!userIdsToKeep.length) {
                        this._setDatasetProperty('targetUsers', 'all');
                    } else if (userIdsToKeep.length !== selectedUserIds.length){
                        this._setDatasetProperty('staffUsers', userIdsToKeep);
                    }
                }
            }
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Logic to apply a similar behavior as for the backend share modal for
     * appointment links, i.e., either
     *   * All appointments and users
     *   * Multiple appointment types with all their staff users
     *   * A single appointment type, allowing to specify only a
     *     subset of its users
     *
     * @override
     * @see this.selectClass for parameters
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        if (params.attributeName in ['targetTypes', 'appointmentTypes', 'targetUsers', 'staffUsers']) {
            this._setDatasetProperty(params.attributeName, widgetValue);
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Update the staff users widget to only allow those from the selected
     * Appointment Type.
     *
     * @override
     */
    async updateUI() {
        this._super(...arguments);

        const selectedAppointmentTypesIds = this._getDatasetProperty('appointmentTypes', true);
        if (selectedAppointmentTypesIds.length) {
            const [staffUsersWidget] = this._requestUserValueWidgets('staff_users_opt');
            return staffUsersWidget.setFilterInDomainIds(selectedAppointmentTypesIds);
        }
    },
    setAppTypes(previewMode, widgetValue, params) {
        this._setDatasetProperty('appointmentTypes', JSON.parse(widgetValue).map(appType => appType.id));
        this._syncAppointmentTypesData();
    },
    setStaffUsers(previewMode, widgetValue, params) {
        this._setDatasetProperty('staffUsers', JSON.parse(widgetValue).map(user => user.id));
        const selectedAppointmentTypesIds = this._getDatasetProperty('appointmentTypes', true);
        this._syncAppointmentTypesData(selectedAppointmentTypesIds[0]);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'setAppTypes') {
            const selectedAppointmentTypes = this._getDatasetProperty('appointmentTypes', true);
            const appointmentTypesDetails = selectedAppointmentTypes.map(id => {
                const appointmentType = this.allAppointmentTypesById[id];
                return {id: appointmentType.id, name: appointmentType.name, display_name: appointmentType.name};
            });
            return JSON.stringify(appointmentTypesDetails);
        }
        if (methodName === 'setStaffUsers') {
            const selectedAppointmentTypes = this._getDatasetProperty('appointmentTypes', true);
            if (selectedAppointmentTypes.length !== 1 || this._getDatasetProperty('targetUsers') === 'all') {
                return '[]';
            }
            const appointmentTypeData = this.allAppointmentTypesById[selectedAppointmentTypes[0]];
            const selectedUserIds = this._getDatasetProperty('staffUsers', true);
            const staffUsersDetails = appointmentTypeData.staff_users
                .filter(user => selectedUserIds.includes(user.id))
                .map(({ id, name }) => ({id, name, display_name: name}));
            return JSON.stringify(staffUsersDetails);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (params.attributeName === 'targetTypes') {
            if (!Object.keys(this.allAppointmentTypesById).length) {
                return false;
            }
        } else if (params.attributeName === 'targetUsers') {
            if (this._getDatasetProperty('targetTypes') === 'all' ||
                this._getDatasetProperty('appointmentTypes', true).length !== 1) {
                return false;
            }
        } else if (params.attributeName === 'appointmentTypes') {
            if (this._getDatasetProperty('targetTypes') === 'all') {
                return false;
            }
        } else if (params.attributeName === 'staffUsers') {
            if (this._getDatasetProperty('targetUsers') === 'all' ||
                    this._getDatasetProperty('appointmentTypes', true).length !== 1) {
                return false;
            }
        }
        return this._super(...arguments);
    },
    /**
     * Helper method to retrieve target dataset properties to increase other
     * methods' readability.
     *
     * @private
     * @param {String} property Name of the target dataset property
     * @param {boolean} parsed `true` to apply JSON.parse before returning
     * @returns {(String | Number[])}
     */
    _getDatasetProperty(property, parsed=false) {
        let value = this.$target[0].dataset[property];
        return parsed ? JSON.parse(value) : value;
    },
    /**
     * Set a target dataset attribute value and trigger cascading updates as
     * necessary. Finally, update the link's form unless prevented.
     *
     * @private
     * @param {"targetTypes" | "appointmentTypes" | "targetUsers" | "staffUsers" } property
     * @param {String | number[]} value
     */
    _setDatasetProperty(property, value) {
        if (property === 'targetTypes') {
            // Change if all or a selection of appointment types. Reset all subsequent parameters
            if (this._getDatasetProperty('targetTypes') !== value) {
                this.$target[0].dataset.targetTypes = value;
                if (this._getDatasetProperty('appointmentTypes', true).length) {
                    this._setDatasetProperty('appointmentTypes', []);
                }
            }
            this._setDatasetProperty('targetUsers', 'all');
        } else if (property === 'appointmentTypes') {
            this.$target[0].dataset.appointmentTypes = JSON.stringify(value);
            if (!value.length) {
                // Explicitly show the behavior when no type is specified
                this._setDatasetProperty('targetTypes', 'all');
            }
            this._setDatasetProperty('targetUsers', 'all');
        } else if (property === 'targetUsers') {
            this.$target[0].dataset.targetUsers = value;
            if (value !== 'specify' || this._getDatasetProperty('appointmentTypes', true).length !== 1) {
                this._setDatasetProperty('staffUsers', []);
            }
        } else if (property === 'staffUsers') {
            this.$target[0].dataset.staffUsers = JSON.stringify(value);
            if (!value.length && this._getDatasetProperty('targetUsers') !== 'all') {
                this._setDatasetProperty('targetUsers', 'all');
            }
        }
    },
    /**
     * Fetches current data about appointment types. Caching is not possible
     * as it could lead to unsynced state with the m2X options fetches.
     *
     * @param {int} [apptId] Only update this record
     * @private
     */
    async _syncAppointmentTypesData(apptId) {
        if (apptId) {
            const record = await this.rpc('/appointment/get_snippet_data', {
                appointment_type_id: apptId,
            });
            if (Object.keys(record).length) {
                this.allAppointmentTypesById[apptId] = record[apptId];
            } else {
                this.allAppointmentTypesById.remove(apptId);
            }
        } else {
            this.allAppointmentTypesById = await this.rpc('/appointment/get_snippet_data');
        }
    },
});
