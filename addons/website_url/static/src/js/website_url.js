(function () {
   'use strict';

    var QWeb = openerp.qweb;

    openerp.website_url = {};
    
    openerp.website_url.RecentLinkBox = openerp.Widget.extend({
        template: 'website_url.RecentLink',
        init: function(parent, link_obj) {
            this._super(parent);
            this.link_obj = link_obj;
        },
        start: function() {
            var self = this;

            new ZeroClipboard(this.$('.btn_shorten_url_clipboard'));

            this.$('.archive').click(function(event) {
                event.preventDefault();
                self.archive();
            });

            this.$('.btn_shorten_url_clipboard').click(function() {
                self.toggle_copy_button();
            });
        },
        archive: function() {
            var self = this;

            openerp.jsonRpc('/r/archive', 'call', {'code' : self.link_obj.code})
                .then(function(result) {
                    self.remove();
                })
                .fail(function() {
                    self.notification('Error: Unable to archive this link.');
                });
        },
        toggle_copy_button: function() {
            var self = this;

            this.clipboard_btn = this.$('.btn_shorten_url_clipboard');
            this.clipboard_btn.text("Copied to clipboard").removeClass("btn-primary").addClass("btn-success");

            setTimeout(function() {
                self.clipboard_btn.text("Copy link to clipboard").removeClass("btn-success").addClass("btn-primary");
            }, '5000');
        },
        remove: function() {
            // this.$el.remove();
            this.getParent().remove_link(this);
        },
        notification: function(message) {
            this.$el.find('.notification').append('<strong>' + message + '</strong>');
        },
    });

    openerp.website_url.RecentLinks = openerp.Widget.extend({
        init: function() {
            this._super();
        },
        start: function($element) {
            var self = this;
            this.$el = $element;

            openerp.website.add_template_file('/website_url/static/src/xml/recent_link.xml')
                .then(function() {
                    self.get_recent_links();
                });
        },
        get_recent_links: function() {
            var self = this;

            openerp.jsonRpc('/r/recent_links', 'call')
                .then(function(result) {
                    // var $recent_links = $('#recent_links');
                    for(var  i = 0 ; i < result.length ; i++) {
                        self.add_link(result[i]);
                    }
                })
                .fail(function() {
                    self.$el.append("<div class='alert alert-danger'>Unable to get recent links</div>");
                });

             this.update_notification();
        },
        add_link: function(link) {
            var self = this;

            // Check if the link is already showed to the user and remove it if it's the case
            var links = this.getChildren();
            for(var i = 0 ; i < links.length ; i++) {
                if(links[i].link_obj.code == link.code) {
                    links[i].remove();
                }
            }

            var recent_link_box = new openerp.website_url.RecentLinkBox(this, link);
            recent_link_box.prependTo(this.$el);

            this.update_notification();
        },
        remove_link: function(link) {
            link.$el.fadeOut(400, function(){ 
                link.$el.remove();
                link.destroy();
            });

            this.update_notification();
        },
        update_notification: function() {
            if(this.getChildren().length == 0) {
                this.$el.find('.notification').append("<div class='alert alert-info'>You don't have any recent links.</div>");
            }
            else {
                this.$el.find('.notification').empty();
            }
        },
    });

    openerp.website_url.SelectBox = openerp.Widget.extend({
        init: function(path) {
            this.path = path;
        },
        start: function($element, placeholder) {
            var self = this;
            this.$element = $element;
            this.placeholder = placeholder;

            this.fetch_objects().then(function(results) {
                self.objects = results;

                $element.select2({
                    initSelection: {id: 0, text: 'Test'},
                    placeholder: self.placeholder,
                    createSearchChoice:function(term, data) {
                        if(self.object_exists(term)) { 
                            return null; 
                        }

                        return {id:term, text:_.str.sprintf("Create '%s'", term)};
                    },
                    createSearchChoicePosition: 'bottom',
                    multiple: false,
                    data: self.objects,
                });

                $element.on('change', function(e) {
                    self.on_change(e);
                });
            });
        },
        fetch_objects: function() {
            return openerp.jsonRpc('/r/' + this.path, 'call').then(function(results) {

                var objects = [];
                for(var i = 0 ; i < results.length ; i++) {
                    objects.push({id: results[i].id, text: results[i].name});
                }
                return objects;
            });
        },
        object_exists: function(query) {
            var self = this;

            for(var i = 0 ; i < self.objects.length ; i++) {
                if(self.objects[i].text.toLowerCase() == query.toLowerCase()) {
                    return true;
                }
            }
            return false;
        },
        on_change: function(e) {
            var self = this;

            if(_.isString(e.added.id)) {
                self.create_object(e.added.id);
            }
        },
        create_object: function(name) {
            var self = this;

            openerp.jsonRpc('/r/' + this.path + '/new', 'call', {name: name})
                .then(function(result) {
                        self.$element.attr('value', result);
                    });
        },
    });

    $(document).ready(function() {

        // Init Widgets
        var recent_links = new openerp.website_url.RecentLinks;
        recent_links.start($("#recent_links"));

        var campaign_select = new openerp.website_url.SelectBox('campaigns');
        campaign_select.start($("#campaign-select"), 'e.g. Promotion of June, Winter Newsletter, ..');

        var medium_select = new openerp.website_url.SelectBox('mediums');
        medium_select.start($("#channel-select"), 'e.g. Newsletter, Social Network, ..');

        var source_select = new openerp.website_url.SelectBox('sources');
        source_select.start($("#source-select"), 'e.g. Search Engine, Website page, ..');

        ZeroClipboard.config(
            {swfPath: location.origin + "/website_url/static/src/js/ZeroClipboard.swf" }
        );

        // Clipboard Library
        var client = new ZeroClipboard($("#btn_shorten_url"));

        // Add the RecentLinkBox widget and send the form when the user generate the link
        $("#btn_shorten_url").click( function() {
            if($(this).attr('class').indexOf('btn_copy') === -1) {
                var url = $("#url").val();
                var campaign_id = $('#campaign-select').attr('value');
                var medium_id = $('#channel-select').attr('value');
                var source_id = $('#source-select').attr('value');

                var params = {};
                params.url = $("#url").val();
                if(campaign_id != '') { params.campaign_id = campaign_id; }
                if(medium_id != '') { params.medium_id = medium_id; }
                if(source_id != '') { params.source_id = source_id; }

                openerp.jsonRpc("/r/new", 'call', params)
                    .then(function (result) {
                        
                        if('error' in result) {
                            var $url_form_group = $('#url-form-group')
                            $url_form_group.addClass('has-error');
                        }
                        else {
                            var link = result[0];
                            $("#url").data("last_result", link.short_url).val(link.short_url).focus().select();
                            $("#url-form-group .control-label").html('Link to share');
                            $("#btn_shorten_url").text("Copy to clipboard").removeClass("btn_shorten btn-primary").addClass("btn_copy btn-success");
                            $("#utms").hide();
                            recent_links.add_link(link);
                        }
                    });
            }
        });

        $("#url").on("change keyup paste mouseup", function() {
            if ($(this).data("last_result") != $("#url").val()) {
                $("#url-form-group .control-label").html('Copy the link to track');
                $("#btn_shorten_url").text("Get tracked link").removeClass("btn_copy btn-success").addClass("btn_shorten btn-primary");
                $('#url-form-group').removeClass('has-error');
                $("#utms").show();
            }
        });
    });
})();