odoo.define_section('ControlPanel.searchview', ['web.ControlPanel', 'web.Widget'], {
    beforeEach: function (assert, ControlPanel, Widget) {
        this.searchview = new (Widget.extend({
            className: 'my_random_class',
            toggle_visibility: function (is_visible) {
                this.$el.toggleClass('o_hidden', !is_visible);
            }
        }))();
        this.searchview.renderElement();
        assert.ok(this.searchview.$el.hasClass('my_random_class'), 'searchview should contain random class');

        var status = {
            hidden: false,
            searchview: this.searchview,
            cp_content: {
                $searchview: this.searchview.$el
            }
        }
        this.controlpanel = new ControlPanel({ });
        this.controlpanel.renderElement();
        this.controlpanel.start();
        this.controlpanel.update(status)

        this.assertSearchNodeVisibility = function assertSearchNodeVisibility(visible, message) {
            var $searchview = this.controlpanel.nodes.$searchview
            var result = !$searchview.hasClass('o_hidden');
            assert.equal(result, visible, message);
        }
        this.assertSearchViewVisibility = function assertSearchViewVisibility(visible, message) {
            var $searchview = this.controlpanel.nodes.$searchview
            this.assert.ok($searchview.has('.my_random_class'), 'SearchView has gone missing');
            var result = !this.searchview.$el.hasClass('o_hidden');
            assert.equal(result, visible, message);
        }
        this.assertSearchVisibility = function assertSearchVisibility(visible, message) {
            this.assertSearchNodeVisibility(visible, "ControlPanel.nodes.$searchview: " + message);
            this.assertSearchViewVisibility(visible, "SearchView.$el: " + message);
        }
    },
},  function (test) {
    test('search view and node visibility by default', function (assert) {
        this.assertSearchVisibility(true, "should be visible if control panel is visible");
    });

    test('search view and node visibility when switched', function (assert) {
        this.controlpanel.update({search_view_hidden: true}, {clear: false})
        this.assertSearchNodeVisibility(false, "search node should turn invisible when requested");
        this.assertSearchViewVisibility(true, "search view itself should not turn invisible if absent from ControlPanel update")
        /*
            notice that, despite not being itself marked invisible, the search view will be de-facto invisible since it's under
            the ControlPanel.nodes.$searchnode in the DOM tree.
        */
        var status = {
            hidden: false,
            searchview: this.searchview,
            search_view_hidden: false
        }
        this.controlpanel.update(status, {clear: false})
        this.assertSearchNodeVisibility(true, "search node should turn back visible when requested");
        this.assertSearchViewVisibility(true, "search view should remain visible")
        var status = {
            hidden: false,
            searchview: this.searchview,
            search_view_hidden: true
        }
        this.controlpanel.update(status, {clear: false})
        this.assertSearchNodeVisibility(false, "search node should turn invisible when requested");
        this.assertSearchViewVisibility(false, "search view should turn invisible when requested and present in the control panel update")
    });

    test('visible search view remains visible if breadcrumb updated', function (assert) {
        this.controlpanel.update({breadcrumbs: [{title: "Breadcrumb 1"}]}, {clear: false});
        this.controlpanel.update({breadcrumbs: [{title: "Breadcrumb 2"}]}, {clear: false});
        this.assertSearchVisibility(true, "search view should remain visible if only breadcrumbs updated");
    });

    test('hidden search view remains hidden if breadcrumb updated', function (assert) {
        var status = {
            hidden: false,
            searchview: this.searchview,
            search_view_hidden: true
        }
        this.controlpanel.update(status, {clear: false});
        this.assertSearchVisibility(false, "should have been hidden");
        this.controlpanel.update({breadcrumbs: [{title: "Breadcrumb 1"}]}, {clear: false});
        this.controlpanel.update({breadcrumbs: [{title: "Breadcrumb 2"}]}, {clear: false});
        this.assertSearchVisibility(false, "should remain hidden if only breadcrumbs updated");
    });

});
