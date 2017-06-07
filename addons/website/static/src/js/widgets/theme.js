odoo.define('website.theme', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var session = require('web.session');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var website = require('website.website');

var QWeb = core.qweb;

ajax.jsonRpc('/web/dataset/call', 'call', {
        'model': 'ir.ui.view',
        'method': 'read_template',
        'args': ['website.theme_customize', base.get_context()]
    }).done(function (data) {
    QWeb.add_template(data);
});

ajax.jsonRpc('/web/dataset/call', 'call', {
        'model': 'ir.ui.view',
        'method': 'read_template',
        'args': ['web_editor.colorpicker', base.get_context()]
    }).done(function (data) {
    QWeb.add_template(data);
});

var Theme = Widget.extend({
    template: 'website.theme_customize',
    events: {
        'change input[data-xmlid],input[data-enable],input[data-disable]': 'change_selection',
        'mousedown label:has(input[data-xmlid],input[data-enable],input[data-disable])': function (event) {
            var self = this;
            this.time_select = _.defer(function () {
                var input = $(event.target).find('input').length ? $(event.target).find('input') : $(event.target).parent().find('input');
                self.on_select(input, event);
            });
        },
        'click .close': 'close',
        'click': 'click',
    },
    start: function () {
        var self = this;
        this.timer = null;
        this.reload = false;
        this.flag = false;
        this.active_select_tags();
        this.$inputs = this.$("input[data-xmlid],input[data-enable],input[data-disable]");
        setTimeout(function () {self.$el.addClass('in');}, 0);
        this.keydown_escape = function (event) {
            if (event.keyCode === 27) {
                self.close();
            }
        };
        $(document).on('keydown', this.keydown_escape);
        return this.load_xml_data().then(function () {
            self.flag = true;
        });
    },
    active_select_tags: function () {
        var uniqueID = 0;
        var self = this;
        var $selects = this.$('select:has(option[data-xmlid],option[data-enable],option[data-disable])');
        $selects.each(function () {
            uniqueID++;
            var $select = $(this);
            var $options = $select.find('option[data-xmlid], option[data-enable], option[data-disable]');
            $options.each(function () {
                var $option = $(this);
                var $input = $('<input style="display: none;" type="radio" name="theme_customize_modal-select-'+uniqueID+'"/>');
                $input.attr('id', $option.attr('id'));
                $input.attr('data-xmlid', $option.data('xmlid'));
                $input.attr('data-enable', $option.data('enable'));
                $input.attr('data-disable', $option.data('disable'));
                $option.removeAttr('id');
                $option.data('input', $input);
                $input.on('update', function () {
                    $option.attr('selected', $(this).prop("checked"));
                });
                self.$el.append($input);
            });
            $select.data("value", $options.first());
            $options.first().attr("selected", true);
        });
        $selects.change(function () {
            var $option = $(this).find('option:selected');
            $(this).data("value").data("input").prop("checked", true).change();
            $(this).data("value", $option);
            $option.data("input").change();
        });
    },
    load_xml_data: function () {
        var self = this;
        $('#theme_error').remove();
        return ajax.jsonRpc('/website/theme_customize_get', 'call', {
            'xml_ids': this.get_xml_ids(this.$inputs)
        }).done(function (data) {
            self.$inputs.filter('[data-xmlid=""]').prop("checked", true).change();
            self.$inputs.filter('[data-xmlid]:not([data-xmlid=""])').each(function () {
                if (!_.difference(self.get_xml_ids($(this)), data[1]).length) {
                    $(this).prop("checked", false).trigger("change", true);
                }
                if (!_.difference(self.get_xml_ids($(this)), data[0]).length) {
                    $(this).prop("checked", true).trigger("change", true);
                }
            });
        }).fail(function (d, error) {
            $('body').prepend($('<div id="theme_error"/>').text(error.data.message));
        });
    },
    get_inputs: function (string) {
        return this.$inputs.filter('#'+string.split(/\s*,\s*/).join(", #"));
    },
    get_xml_ids: function ($inputs) {
        var xml_ids = [];
        $inputs.each(function () {
            if ($(this).data('xmlid') && $(this).data('xmlid').length) {
                xml_ids = xml_ids.concat($(this).data('xmlid').split(/\s*,\s*/));
            }
        });
        return xml_ids;
    },
    update_style: function (enable, disable, reload) {
        if (this.$el.hasClass("loading")) {
            return;
        }
        this.$el.addClass('loading');

        if (!reload && session.debug !== "assets") {
            var self = this;
            return ajax.jsonRpc('/website/theme_customize', 'call', {
                enable: enable,
                disable: disable,
                get_bundle: true,
            }).then(function (bundleHTML) {
                var $links = $('link[href*=".assets_frontend"]');
                var $newLinks = $(bundleHTML).filter('link');

                var linksLoaded = $.Deferred();
                var nbLoaded = 0;
                $newLinks.on('load', function (e) {
                    if (++nbLoaded >= $newLinks.length) {
                        linksLoaded.resolve();
                    }
                });
                $newLinks.on('error', function (e) {
                    linksLoaded.reject();
                    window.location.hash = "theme=true";
                    window.location.reload();
                });

                $links.last().after($newLinks);
                return linksLoaded.then(function () {
                    $links.remove();
                    self.$el.removeClass('loading');
                });
            });
        } else {
            var href = '/website/theme_customize_reload'+
                '?href='+encodeURIComponent(window.location.href)+
                '&enable='+encodeURIComponent(enable.join(","))+
                '&disable='+encodeURIComponent(disable.join(","));
            window.location.href = href;
            return $.Deferred();
        }
    },
    enable_disable: function ($inputs, enable) {
        $inputs.each(function () {
            var check = $(this).prop("checked");
            var $label = $(this).closest("label");
            $(this).prop("checked", enable);
            if (enable) $label.addClass("checked");
            else $label.removeClass("checked");
            if (check != enable) {
                $(this).change();
            }
        });
    },
    change_selection: function (event, init_mode) {
        var self = this;
        clearTimeout(this.time_select);

        if (this.$el.hasClass("loading")) return; // prevent to change selection when css is loading
            
        var $option = $(event.target).is('input') ? $(event.target) : $("input", event.target),
            $options = $option,
            checked = $option.prop("checked");

        if (checked) {
            if($option.data('enable')) {
                var $inputs = this.get_inputs($option.data('enable'));
                $options = $options.add($inputs.filter(':not(:checked)'));
                this.enable_disable($inputs, true);
            }
            if($option.data('disable')) {
                var $inputs = this.get_inputs($option.data('disable'));
                $options = $options.add($inputs.filter(':checked'));
                this.enable_disable($inputs, false);
            }
            $option.closest("label").addClass("checked");
        } else {
            $option.closest("label").removeClass("checked");
        }

        var $enable = this.$inputs.filter('[data-xmlid]:checked');
        $enable.closest("label").addClass("checked");
        var $disable = this.$inputs.filter('[data-xmlid]:not(:checked)');
        $disable.closest("label").removeClass("checked");

        var $sets = this.$inputs.filter('input[data-enable]:not([data-xmlid]), input[data-disable]:not([data-xmlid])');
        $sets.each(function () {
            var $set = $(this);
            var checked = true;
            if ($set.data("enable")) {
                self.get_inputs($(this).data("enable")).each(function () {
                    if (!$(this).prop("checked")) checked = false;
                });
            }
            if ($set.data("disable")) {
                self.get_inputs($(this).data("disable")).each(function () {
                    if ($(this).prop("checked")) checked = false;
                });
            }
            if (checked) {
                $set.prop("checked", true).closest("label").addClass("checked");
            } else {
                $set.prop("checked", false).closest("label").removeClass("checked");
            }
            $set.trigger('update');
        });

        if (this.flag && $option.data('reload') && document.location.href.match(new RegExp( $option.data('reload') ))) {
            this.reload = true;
        }

        clearTimeout(this.timer);
        if (this.flag) {
            this.timer = _.defer(function () {
                if (!init_mode) self.on_select($options, event);
                self.update_style(self.get_xml_ids($enable), self.get_xml_ids($disable), self.reload);
                self.reload = false;
            });
        } else {
                this.timer = _.defer(function () {
                    if (!init_mode) self.on_select($options, event);
                    self.reload = false;
                });
        }
    },
    /* Method call when the user change the selection or click on an input
     * @values: all changed inputs
     */
    on_select: function ($inputs, event) {
        clearTimeout(this.time_select);
    },
    click: function (event) {
        if (!$(event.target).closest("#theme_customize_modal > *").length) {
            this.close();
        }
    },
    close: function () {
        var self = this;
        $(document).off('keydown', this.keydown_escape);
        $('#theme_error').remove();
        $('link[href*=".assets_"]').removeAttr('data-loading');
        this.$el.removeClass('in');
        this.$el.addClass('out');
        setTimeout(function () {self.destroy();}, 500);
    }
});

function themeError(message) {
    var _t = core._t;

    if (message.indexOf('lessc')) {
        message = '<span class="text-muted">' + message + "</span><br/><br/>" + _t("Please install or update node-less");
    }

    website.error(_t("Theme Error"), message);
}

function theme_customize() {
    if (Theme.open && !Theme.open.isDestroyed()) return;
    Theme.open = new Theme();
    Theme.open.appendTo("body");
    
    var error = window.getComputedStyle(document.body, ':before').getPropertyValue('content');
    if (error && error !== 'none') {
        themeError(eval(error));
    }
}

website.TopBar.include({
    start: function () {
        var self = this;
        base.ready().then(function () {
            self.$el.on('click', "#theme_customize a", theme_customize);
            if ((window.location.hash || "").indexOf("theme=true") !== -1) {
                theme_customize();
                window.location.hash = "";
            }
        });

        return this._super();
    }
});

return Theme;

});
