odoo.define('hr.StandaloneM2OAvatarEmployee', function (require) {
    'use strict';

    const StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    const Widget = require('web.Widget');

    const { Many2OneAvatarEmployee } = require('hr.Many2OneAvatarEmployee');

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

    return StandaloneM2OAvatarEmployee;
});
