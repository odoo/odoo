odoo.define("hr/static/src/js/standalone_avatar_employee_adapter", function (require) {
    "use strict";

    const { ComponentAdapter } = require('web.OwlCompatibility');

    class StandaloneAvatarEmployeeAdapter extends ComponentAdapter {

        /**
         * @override
         */
        renderWidget() { }

        /**
         * @override
         */
        async updateWidget(nextProps) {
            if (JSON.stringify(this.props.value) === JSON.stringify(nextProps.value)) {
                return;
            }
            const state = nextProps.value;
            await this.widget.avatarWidget.reinitialize(state);
        }
    }

    return StandaloneAvatarEmployeeAdapter;
});
