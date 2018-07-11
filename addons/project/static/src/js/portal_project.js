/**
 * In order to inject a "backend view" into the DOM, a <portal-project/> element
 * has to be present and contain t-att-data params. At the very least these params must
 * contain the viewType key (= 'kanban' or 'form'). The other keys depend on the viewType.
 * To see the list of requested parameters, see the respective definitions for the viewType.
 * In order to add a search view, the <portal-project/> element must contain t-att-data options
 * with the key 'search' = true. A search view is not possible on a form.
 */
odoo.define('project.portal_project', function (require) {
    require('web.dom_ready');
    var config = require('web.config');
    var webClient = require('web.web_client');

    var $target = $('portal-project');

    if (!$target.length) {
        return $.Deferred().reject("DOM doesn't contain 'portal-project'");
    };
    if (!$target.data('params')) {
        return $.Deferred().reject("No params were passed to 'portal-project'")
    };

    var params = $target.data('params');
    var options = $target.data('options') || {};
    switch (params['viewType']) {
        case 'kanban':
            var PortalKanban = require('project.PortalKanban');
            var portalKanban = new PortalKanban(webClient, params, options);
            portalKanban.appendTo($target);
            break;
        case 'form':
            var PortalForm = require('project.PortalForm');
            var portalForm = new PortalForm(webClient, params, options);
            portalForm.appendTo($target);
            break;
        default:
            return $.Deferred().reject("No view type was specified in the params passed to 'portal-project'");
    };

    // Observe every change in the DOM to resize the iFrame according to its contents' height

    var observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            if (config.device.isMobile && params['viewType'] === 'kanban') {
                adjustPositions();
            };
            resizeIFrame();
        });
    });

    observer.observe(document.body, {
        attributes: true,
        characterData: true,
        childList: true,
        subtree: true,
    });
    
    function resizeIFrame() {
        $(window.top.document).find('iframe').height(1).height(document.body.scrollHeight);
    };

    /**
     * For responsivity purposes, the position of kanban groups is made relative when shown
     * (when the group's id is the id of the current tab) and absolute when hidden. This is
     * to make the height of the body reflect the real height of the document, for use with
     * resizing of the iframe.
     */
    function adjustPositions() {
        $('.o_kanban_group').each(function () {
            if ($('.o_current').attr('data-id') === $(this).attr('data-id')) {
                $(this).css('position', 'relative');
            } else {
                $(this).css('position', 'absolute');
            };
        });
    };
});
