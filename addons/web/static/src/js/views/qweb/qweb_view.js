/**
 * Client-side implementation of a qweb view.
 */
odoo.define('web.qweb', function (require) {
"use strict";

var core = require('web.core');
var AbstractView = require('web.AbstractView');
var AbstractModel = require('web.AbstractModel');
var AbstractRenderer = require('web.AbstractRenderer');
var AbstractController = require('web.AbstractController');
var registry = require('web.view_registry');

var _lt = core._lt;

/**
 * model
 */
var Model = AbstractModel.extend({
    /**
     * init
     */
    init: function () {
        this._super.apply(this, arguments);
        this._state = {
            viewId: false,
            modelName: false,
            body: '',
            context: {},
            domain: [],
        };
    },
    /**
     * fetches the rendered qweb view
     */
    _fetch: function () {
        var state = this._state;
        return this._rpc({
            model: state.modelName,
            method: 'qweb_render_view',
            kwargs: {
                view_id: state.viewId,
                domain: state.domain,
                context: state.context
            }
        }).then(function (r) {
            state.body = r;
            return state.viewId;
        });
    },
    /**
     * get
     */
    __get: function () {
        return this._state;
    },
    /**
     * load
     */
    __load: function (params) {
        _.extend(this._state, _.pick(params, ['viewId', 'modelName', 'domain', 'context']));

        return this._fetch();
    },
    /**
     * reload
     */
    __reload: function (_id, params) {
        _.extend(this._state, _.pick(params, ['domain', 'context']));

        return this._fetch();
    }
});
/**
 * renderer
 */
var Renderer = AbstractRenderer.extend({
    /**
     * render
     */
    _render: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$el.html(self.state.body);
        });
    }
});
/**
 * controller
 */
var Controller = AbstractController.extend({
    events: _.extend({}, AbstractController.prototype.events, {
        'click [type="toggle"]': '_onLazyToggle',
        'click [type="action"]' : '_onActionClicked',
    }),

    init: function () {
        this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    renderButtons: function ($node) {
        this.$buttons = $('<nav/>');
        if ($node) {
            $node.append(this.$buttons);
        }
    },
    _update: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            // move control panel buttons from the view to the control panel
            // area
            var $cp_buttons = self.renderer.$('nav.o_qweb_cp_buttons');
            $cp_buttons.children().appendTo(self.$buttons.empty());
            $cp_buttons.remove();
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Lazy toggle. Content is not remembered between unfolds.
     */
    _onLazyToggle: function (e) {
        // TODO: add support for view (possibly action as well?)
        var $target = $(e.target);
        var $t = $target.closest('[data-model]');
        if (!($target.hasClass('fa-caret-down') || $target.hasClass('fa-caret-right'))) {
            $target = $t.find('.fa-caret-down, .fa-caret-right');
        }

        var data = $t.data();
        if (this._fold($t)) {
            $target.removeClass('fa-caret-down').addClass('fa-caret-right');
            return;
        }

        // NB: $.data() automatically parses json attributes, but does not
        //     automatically parse lone float literals in data-*, so a
        //     data-args (as a json object) is very convenient
        var args = data.args || _.omit(data, 'model', 'method', 'id');

        return this._rpc({
            model: data.model,
            method: data.method,
            args: data.id ? [data.id] : undefined,
            kwargs: args // FIXME: context?
        }).then(function (s) {
            return $(s);
        }).then(function ($newcontent) {
            $t.data('children', $newcontent).after($newcontent);
            $target.removeClass('fa-caret-right').addClass('fa-caret-down');
        });
    },
    /**
     * Attempts to fold the parameter, returns whether that happened.
     */
    _fold: function ($el) {
        var $children = $el.data('children');
        if (!$children) {
            return false;
        }

        var self = this;
        $children.each(function (_i, e) {
            self._fold($(e));
        }).remove();
        $el.removeData('children');
        return true;
    }
});

/**
 * view
 */
var QWebView = AbstractView.extend({
    display_name: _lt('Freedom View'),
    icon: 'fa-file-picture-o',
    viewType: 'qweb',
    // groupable?
    enableTimeRangeMenu: true,
    config: _.extend({}, AbstractView.prototype.config, {
        Model: Model,
        Renderer: Renderer,
        Controller: Controller,
    }),

    /**
     * init method
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        this.loadParams.viewId = viewInfo.view_id;
    }
});

registry.add('qweb', QWebView);
return {
    View: QWebView,
    Controller: Controller,
    Renderer: Renderer,
    Model: Model
};
});
