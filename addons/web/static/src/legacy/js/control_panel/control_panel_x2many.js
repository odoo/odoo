odoo.define('web.ControlPanelX2Many', function (require) {

    const ControlPanel = require('web.ControlPanel');

    /**
     * Control panel (adaptation for x2many fields)
     *
     * Smaller version of the control panel with an abridged template (buttons and
     * pager only). We still extend the main version for the injection of `cp_content`
     * keys.
     * The pager of this control panel is only displayed if the amount of records
     * cannot be displayed in a single page.
     * @extends ControlPanel
     */
    class ControlPanelX2Many extends ControlPanel {

        /**
         * @private
         * @returns {boolean}
         */
        _shouldShowPager() {
            if (!this.props.pager || !this.props.pager.limit) {
                return false;
            }
            const { currentMinimum, limit, size } = this.props.pager;
            const maximum = Math.min(currentMinimum + limit - 1, size);
            const singlePage = (1 === currentMinimum) && (maximum === size);
            return !singlePage;
        }
    }

    ControlPanelX2Many.defaultProps = {};
    ControlPanelX2Many.props = {
        cp_content: { type: Object, optional: 1 },
        pager: Object,
    };
    ControlPanelX2Many.template = 'web.ControlPanelX2Many';

    return ControlPanelX2Many;
});
