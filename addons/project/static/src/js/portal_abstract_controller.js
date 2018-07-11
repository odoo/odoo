odoo.define('project.portal_abstract_controller', function (require) {

var AbstractController = require('web.AbstractController');

/**
 * Performs various overrides on AbstractController.
 * - ensures that a task opens when clicking it
 * - ensures that the control elements are not rendered
 */
AbstractController.include({
    /**
     * Opens a task on click
     * Note: doesn't open a project on click because clicking a
     *       project fires a 'button_clicked' event instead of an
     *       open_record' event (because the action type is 'object'
     *       and not 'open': see kanban_record.js > _onKanbanActionClicked)
     *
     * @override
     * @param {OdooEvent} event
     */
    _onOpenRecord: function (event) {
        var id = event.target.id || event.data.id ? this.model.get(event.data.id).data.id : undefined;
        var topLocation = window.top.location;
        topLocation.href = topLocation.origin + '/my/task/' + id + topLocation.search + topLocation.hash;
    },
    /**
     * Prevent rendering of Control Panel elements
     *
     * @override
     */
    _renderControlPanelElements: function () {
    },
});
});
