odoo.define('website_links.website_links', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var rpc = require('web.rpc');
var Widget = require('web.Widget');
var base = require('web_editor.base');
var website = require('website.website');

var qweb = core.qweb;
var _t = core._t;
var ZeroClipboard = window.ZeroClipboard;

var exports = {};

if(!$('.o_website_links_create_tracked_url').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_website_links_create_tracked_url'");
}

    var SelectBox = Widget.extend({
        init: function(obj) {
            this.obj = obj;
        },
        start: function(element, placeholder) {
            var self = this;
            this.element = element;
            this.placeholder = placeholder;

            this.fetch_objects().then(function(results) {
                self.objects = results;

                element.select2({
                    placeholder: self.placeholder,
                    allowClear: true,
                    createSearchChoice:function(term) {
                        if(self.object_exists(term)) { return null; }

                        return {id:term, text:_.str.sprintf("Create '%s'", term)};
                    },
                    createSearchChoicePosition: 'bottom',
                    multiple: false,
                    data: self.objects,
                });

                element.on('change', function(e) {
                    self.on_change(e);
                });
            });
        },
        fetch_objects: function() {
            return rpc.query({
                    model: this.obj,
                    method: 'search_read',
                })
                .then(function(result) {
                    return _.map(result, function(val) {
                        return {id: val.id, text:val.name};
                    });
                });
        },
        object_exists: function(query) {
            return _.find(this.objects, function(val) {
                return val.text.toLowerCase() === query.toLowerCase();
            }) !== undefined;
        },
        on_change: function(e) {
            if(e.added && _.isString(e.added.id)) {
                this.create_object(e.added.id);
            }
        },
        create_object: function(name) {
            var self = this;

            return rpc.query({
                    model: this.obj,
                    method: 'create',
                    args: [{name:name}],
                })
                .then(function(record) {
                    self.element.attr('value', record);
                    self.objects.push({'id': record, 'text': name});
                });
        },
    });
    
    var RecentLinkBox = Widget.extend({
        template: 'website_links.RecentLink',
        events: {
            'click .btn_shorten_url_clipboard':'toggle_copy_button',
            'click .o_website_links_edit_code':'edit_code',
            'click .o_website_links_ok_edit':function(e) {
                e.preventDefault();
                this.submit_code();
            },
            'click .o_website_links_cancel_edit':function(e) {
                e.preventDefault();
                this.cancel_edit();
            },
            'submit #o_website_links_edit_code_form':function(e) {
                e.preventDefault();
                this.submit_code();
            },
        },
        init: function(parent, link_obj) {
            this._super(parent);
            this.link_obj = link_obj;
            this.animating_copy = false;
        },
        start: function() {
            new ZeroClipboard(this.$('.btn_shorten_url_clipboard'));
        },
        toggle_copy_button: function() {
            var self = this;

            if(!this.animating_copy) {
                this.animating_copy = true;
                var top = this.$('.o_website_links_short_url').position().top;
                this.$('.o_website_links_short_url').clone()
                    .css('position', 'absolute')
                    .css('left', 15)
                    .css('top', top-2)
                    .css('z-index', 2)
                    .removeClass('o_website_links_short_url')
                    .addClass('animated-link')
                    .insertAfter(this.$('.o_website_links_short_url'))
                    .animate({
                        opacity: 0,
                        top: "-=20",
                    }, 500, function() {
                        self.$('.animated-link').remove();
                        self.animating_copy = false;
                    });
            }
        },
        remove: function() {
            this.getParent().remove_link(this);
        },
        notification: function(message) {
            this.$('.notification').append('<strong>' + message + '</strong>');
        },
        edit_code: function() {
            var init_code = this.$('#o_website_links_code').html();

            this.$('#o_website_links_code').html("<form style='display:inline;' id='o_website_links_edit_code_form'><input type='hidden' id='init_code' value='" + init_code + "'/><input type='text' id='new_code' value='" + init_code + "'/></form>");
            this.$('.o_website_links_edit_code').hide();
            this.$('.copy-to-clipboard').hide();
            this.$('.o_website_links_edit_tools').show();
        },
        cancel_edit: function() {
            this.$('.o_website_links_edit_code').show();
            this.$('.copy-to-clipboard').show();
            this.$('.o_website_links_edit_tools').hide();
            this.$('.o_website_links_code_error').hide();

            var old_code = this.$('#o_website_links_edit_code_form #init_code').val();
            this.$('#o_website_links_code').html(old_code);

            this.$('#code-error').remove();
            this.$('#o_website_links_code form').remove();
        },
        submit_code: function() {
            var self = this;

            var init_code = this.$('#o_website_links_edit_code_form #init_code').val();
            var new_code = this.$('#o_website_links_edit_code_form #new_code').val();

            if(new_code === '') {
                self.$('.o_website_links_code_error').html("The code cannot be left empty");
                self.$('.o_website_links_code_error').show();
                return;
            }

            function show_new_code(new_code) {
                self.$('.o_website_links_code_error').html('');
                self.$('.o_website_links_code_error').hide();

                self.$('#o_website_links_code form').remove();

                // Show new code
                var host = self.$('#o_website_links_host').html();
                self.$('#o_website_links_code').html(new_code);

                // Update button copy to clipboard
                self.$('.btn_shorten_url_clipboard').attr('data-clipboard-text', host + new_code);
                
                // Show action again
                self.$('.o_website_links_edit_code').show();
                self.$('.copy-to-clipboard').show();
                self.$('.o_website_links_edit_tools').hide();
            }

            if(init_code == new_code) {
                show_new_code(new_code);
            }
            else {
                ajax.jsonRpc('/website_links/add_code', 'call', {'init_code':init_code, 'new_code':new_code})
                    .then(function(result) {
                        show_new_code(result[0].code);
                    })
                    .fail(function() {
                        self.$('.o_website_links_code_error').show();
                        self.$('.o_website_links_code_error').html("This code is already taken");
                    }) ;
            }
        },
    });

    var RecentLinks = Widget.extend({
        init: function() {
            this._super();
        },
        get_recent_links: function(filter) {
            var self = this;

            ajax.jsonRpc('/website_links/recent_links', 'call', {'filter':filter, 'limit':20})
                .then(function(result) {
                    _.each(result.reverse(), function(link) {
                        self.add_link(link);
                    });

                    self.update_notification();
                })
                .fail(function() {
                    var message = _t("Unable to get recent links");
                    self.$el.append("<div class='alert alert-danger'>" + message + "</div>");
                });            
        },
        add_link: function(link) {
            var nb_links = this.getChildren().length;

            var recent_link_box = new RecentLinkBox(this, link);
            recent_link_box.prependTo(this.$el);
            $('.link-tooltip').tooltip();

            if(nb_links === 0) {
                this.update_notification();
            }
        },
        remove_links: function() {
            _.invoke(this.getChildren(), 'remove');
        },
        remove_link: function(link) {
            link.destroy();
        },
        update_notification: function() {
            if(this.getChildren().length === 0) {
                var message = _t("You don't have any recent links.");
                $('.o_website_links_recent_links_notification').html("<div class='alert alert-info'>" + message + "</div>");
            }
            else {
                $('.o_website_links_recent_links_notification').empty();
            }
        },
    });

    ajax.loadXML('/website_links/static/src/xml/recent_link.xml', qweb);

    base.ready().done(function() {

        ZeroClipboard.config({swfPath: location.origin + "/website_links/static/lib/zeroclipboard/ZeroClipboard.swf" });

        // UTMS selects widgets
        var campaign_select = new SelectBox('utm.campaign');
        campaign_select.start($("#campaign-select"), _t('e.g. Promotion of June, Winter Newsletter, ..'));

        var medium_select = new SelectBox('utm.medium');
        medium_select.start($("#channel-select"), _t('e.g. Newsletter, Social Network, ..'));

        var source_select = new SelectBox('utm.source');
        source_select.start($("#source-select"), _t('e.g. Search Engine, Website page, ..'));

        // Recent Links Widgets
        var recent_links = new RecentLinks();
            recent_links.appendTo($("#o_website_links_recent_links"));
            recent_links.get_recent_links('newest');

        $('#filter-newest-links').click(function() {
            recent_links.remove_links();
            recent_links.get_recent_links('newest');
        });

        $('#filter-most-clicked-links').click(function() {
            recent_links.remove_links();
            recent_links.get_recent_links('most-clicked');
        });

        $('#filter-recently-used-links').click(function() {
            recent_links.remove_links();
            recent_links.get_recent_links('recently-used');
        });
        
        // Clipboard Library
        var client = new ZeroClipboard($("#btn_shorten_url"));

        $("#generated_tracked_link a").click(function() {
            $("#generated_tracked_link a").text("Copied").removeClass("btn-primary").addClass("btn-success");
            setTimeout(function() {
                $("#generated_tracked_link a").text("Copy").removeClass("btn-success").addClass("btn-primary");
            }, '5000');
        });

        $('#url').on('keyup', function(e) {
            if($('#btn_shorten_url').hasClass('btn-copy') && e.which != 13) {
                $('#btn_shorten_url').removeClass('btn-success btn-copy').addClass('btn-primary').html('Get tracked link');
                $('#generated_tracked_link').css('display', 'none');
                $('.o_website_links_utm_forms').show();
            }
        });

        var url_copy_animating = false;
        $('#btn_shorten_url').click(function() {
            if($('#btn_shorten_url').hasClass('btn-copy')) {
                if(!url_copy_animating) {
                    url_copy_animating = true;

                    $('#generated_tracked_link').clone()
                        .css('position', 'absolute')
                        .css('left', '78px')
                        .css('bottom', '8px')
                        .css('z-index', 2)
                        .removeClass('#generated_tracked_link')
                        .addClass('url-animated-link')
                        .appendTo($('#generated_tracked_link'))
                        .animate({
                            opacity: 0,
                            bottom: "+=20",
                        }, 500, function() {
                            $('.url-animated-link').remove();
                            url_copy_animating = false;
                        });
                }
            }
        });
        
        // Add the RecentLinkBox widget and send the form when the user generate the link
        $("#o_website_links_link_tracker_form").submit(function(event) {

            if($('#btn_shorten_url').hasClass('btn-copy')) {
                event.preventDefault();
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            // Get URL and UTMs
            var url = $("#url").val();
            var campaign_id = $('#campaign-select').attr('value');
            var medium_id = $('#channel-select').attr('value');
            var source_id = $('#source-select').attr('value');

            var params = {};
            params.url = $("#url").val();
            if(campaign_id !== '') { params.campaign_id = parseInt(campaign_id); }
            if(medium_id !== '') { params.medium_id = parseInt(medium_id); }
            if(source_id !== '') { params.source_id = parseInt(source_id); }

            $('#btn_shorten_url').text(_t('Generating link...'));

            ajax.jsonRpc("/website_links/new", 'call', params)
                .then(function (result) {
                    if('error' in result) {
                        // Handle errors
                        if(result.error === 'empty_url')  {
                            $('.notification').html("<div class='alert alert-danger'>The URL is empty.</div>");
                        }
                        else if(result.error == 'url_not_found') {
                            $('.notification').html("<div class='alert alert-danger'>URL not found (404)</div>");
                        }
                        else {
                            $('.notification').html("<div class='alert alert-danger'>An error occur while trying to generate your link. Try again later.</div>");
                        }
                    }
                    else {
                        // Link generated, clean the form and show the link
                        var link = result[0];

                        $('#btn_shorten_url').removeClass('btn-primary').addClass('btn-success btn-copy').html('Copy');
                        $('#btn_shorten_url').attr('data-clipboard-text', link.short_url);

                        $('.notification').html('');
                        $('#generated_tracked_link').html(link.short_url);
                        $('#generated_tracked_link').css('display', 'inline');

                        recent_links.add_link(link);

                        // Clean URL and UTM selects
                        $('#campaign-select').select2('val', '');
                        $('#channel-select').select2('val', '');
                        $('#source-select').select2('val', '');

                        $('.o_website_links_utm_forms').hide();
                    }
                });
        });

        $(function () {
          $('[data-toggle="tooltip"]').tooltip();
        });
    });

    exports.SelectBox = SelectBox;
    exports.RecentLinkBox = RecentLinkBox;
    exports.RecentLinks = RecentLinks;

return exports;
});
