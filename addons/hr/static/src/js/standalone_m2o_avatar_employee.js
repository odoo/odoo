/** @odoo-module **/

    import StandaloneFieldManagerMixin from 'web.StandaloneFieldManagerMixin';
    import Widget from 'web.Widget';

    import { Many2OneAvatarEmployee } from '@hr/js/m2x_avatar_employee';

    const StandaloneM2OAvatarEmployee = Widget.extend(StandaloneFieldManagerMixin, {
        className: 'o_standalone_avatar_employee',

        /**
         * @override
         */
        init(parent, value) {
            this._super(...arguments);
            StandaloneFieldManagerMixin.init.call(this);
            this.value = value;
        },
        /**
         * @override
         */
        willStart() {
            return Promise.all([this._super(...arguments), this._makeAvatarWidget()]);
        },
        /**
         * @override
         */
        start() {
            this.avatarWidget.$el.appendTo(this.$el);
            return this._super(...arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Create a record, and initialize and start the avatar widget.
         *
         * @private
         * @returns {Promise}
         */
        async _makeAvatarWidget() {
            const modelName = 'hr.employee';
            const fieldName = 'employee_id';
            const recordId = await this.model.makeRecord(modelName, [{
                name: fieldName,
                relation: modelName,
                type: 'many2one',
                value: this.value,
            }]);
            const state = this.model.get(recordId);
            this.avatarWidget = new Many2OneAvatarEmployee(this, fieldName, state);
            this._registerWidget(recordId, fieldName, this.avatarWidget);
            return this.avatarWidget.appendTo(document.createDocumentFragment());
        },
    });

    export default StandaloneM2OAvatarEmployee;
