(function () {
   'use strict';

    var QWeb = openerp.qweb;

    openerp.website_url = {};

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
                    allowClear: true,
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

            if(e.added && _.isString(e.added.id)) {
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

            this.$el.hover(function() {
                self.$el.find('.recent_link_buttons').show();
            }, function() {
                self.$el.find('.recent_link_buttons').hide();
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
            this.clipboard_btn.text("Copied to clipboard").removeClass("btn-default").addClass("btn-success");

            setTimeout(function() {
                self.clipboard_btn.text("Copy to clipboard").removeClass("btn-success").addClass("btn-default");
            }, '5000');
        },
        remove: function() {
            this.getParent().remove_link(this);
        },
        notification: function(message) {
            this.$el.find('.notification').append('<strong>' + message + '</strong>');
        },
    });

    openerp.website_url.RecentLinks = openerp.Widget.extend({
        init: function($element) {
            this._super();
            this.$el = $element;
        },
        start: function() {
            var self = this;
        },
        get_recent_links: function(filter) {
            var self = this;
            var nb_links = this.getChildren().length;

            openerp.jsonRpc('/r/recent_links', 'call', {'filter':filter.code})
                .then(function(result) {
                    var ordered_result = result.reverse();
                    for(var  i = 0 ; i < ordered_result.length ; i++) {
                        self.add_link(ordered_result[i]);
                    }

                    if(nb_links == 0) {
                        self.update_notification();
                    }
                })
                .fail(function() {
                    self.$el.append("<div class='alert alert-danger'>Unable to get recent links</div>");
                });            
        },
        add_link: function(link) {
            var self = this;
            var nb_links = this.getChildren().length;

            var recent_link_box = new openerp.website_url.RecentLinkBox(this, link);
            recent_link_box.prependTo(this.$el);

            if(nb_links == 0) {
                this.update_notification();
            }
        },
        remove_links: function() {
            var links = this.getChildren();
            for(var i = 0 ; i < links.length ; i++) {
                links[i].remove();
            }
        },
        remove_link: function(link) {
            link.$el.remove();
            link.destroy();
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

    openerp.website_url.Filter = openerp.Widget.extend({
        init: function(parent, name, code) {
            this._super(parent);
            this.name = name;
            this.code = code;
            this.prefix = 'link-filter-';
        },
        get_link: function() {
            return "<li id='"+ this.prefix + this.code + "'><a  href='#'>" + this.name + "</a></li>";
        },
        get_span: function() {
            return "<li class='active' id='" + this.prefix + this.code + "'><a>" + this.name + "</a></li>";
        },
        activate: function() {
            var self = this;

            $('#' + this.prefix + this.code).on("click", function(event) {
                    event.preventDefault();
                    self.getParent().select_filter(self);
                });
        },
        desactivate: function() {
            $('#' + this.prefix + this.code).off();
        },
    });

    openerp.website_url.Filters = openerp.Widget.extend({
        init: function(recent_links) {
            this._super();
            this.recent_links = recent_links;
        },
        start: function() {
            var self = this;
            this.selected = false;

            this.filters = [];
            this.filters.push(new openerp.website_url.Filter(this, 'Newest', 'newest'));
            this.filters.push(new openerp.website_url.Filter(this, 'Most Clicked', 'most-clicked'));
            this.filters.push(new openerp.website_url.Filter(this, 'Recently Used', 'recently-used'));

            // Display the widget inline
            this.$el.closest('div').attr('style', 'display:inline;');
            
            var html_filters = _.map(this.filters, function (f) {
                return f.get_link();
            });
            this.$el.replaceWith(html_filters.join(''));

            _.each(this.filters, function (f) {
                f.activate();
            });

            this.select_filter(this.filters[0]);
        },
        select_filter: function(filter) {
            this.recent_links.remove_links();
            this.recent_links.get_recent_links(filter);
            this.update_selected_filter(filter);
        },
        update_selected_filter: function(filter) {
            var self = this;

            _.each(this.filters, function(f) {
                if(f == self.selected) {
                    $('#link-filter-' + f.code).replaceWith(f.get_link());
                    f.activate();
                }

                if(f == filter) {
                    f.desactivate();
                    $('#link-filter-' + f.code).replaceWith(f.get_span());
                }
            });

            this.selected = filter;
        },
    });

    $(document).ready(function() {

        ZeroClipboard.config({swfPath: location.origin + "/website_url/static/src/js/ZeroClipboard.swf" });

        // Init Widgets
        var campaign_select = new openerp.website_url.SelectBox('campaigns');
        campaign_select.start($("#campaign-select"), 'e.g. Promotion of June, Winter Newsletter, ..');

        var medium_select = new openerp.website_url.SelectBox('mediums');
        medium_select.start($("#channel-select"), 'e.g. Newsletter, Social Network, ..');

        var source_select = new openerp.website_url.SelectBox('sources');
        source_select.start($("#source-select"), 'e.g. Search Engine, Website page, ..');

        var recent_links;
        openerp.website.add_template_file('/website_url/static/src/xml/recent_link.xml')
            .then(function() {
                    recent_links = new openerp.website_url.RecentLinks($("#recent_links"));
                    var filters = new openerp.website_url.Filters(recent_links);
                    filters.appendTo($('#filters-links'));
                });
        
        // Clipboard Library
        var client = new ZeroClipboard($("#btn_shorten_url"));

        // Add the RecentLinkBox widget and send the form when the user generate the link
        $("#link-tracker-form").submit(function(event) {

            event.preventDefault();

            if($('#btn_shorten_url').attr('class').indexOf('btn_copy') === -1) {
                var url = $("#url").val();
                var campaign_id = $('#campaign-select').attr('value');
                var medium_id = $('#channel-select').attr('value');
                var source_id = $('#source-select').attr('value');

                var params = {};
                params.url = $("#url").val();
                if(campaign_id != '') { params.campaign_id = campaign_id; }
                if(medium_id != '') { params.medium_id = medium_id; }
                if(source_id != '') { params.source_id = source_id; }

                $("#btn_shorten_url").text('Generating link...');

                openerp.jsonRpc("/r/new", 'call', params)
                    .then(function (result) {
                        if('error' in result) {
                            var $url_form_group = $('#url-form-group')
                            $url_form_group.addClass('has-error');

                            if(result['error'] == 'empty_url')  {
                                $('.notification').html("<div class='alert alert-danger'>The URL is empty.</div>");
                            }
                            else if(result['error'] == 'url_not_found') {
                                $('.notification').html("<div class='alert alert-danger'>URL not found (404)</div>");
                            }
                        }
                        else {
                            var link = result[0];
                            $('.notification').html('');
                            $("#url").data("last_result", link.short_url).val(link.short_url).focus().select();
                            $("#url-form-group .control-label").html('To share');
                            $("#btn_shorten_url").text("Copy to clipboard").removeClass("btn_shorten btn-primary").addClass("btn_copy btn-success");
                            recent_links.add_link(link);

                            // Clean UTM selects
                            $('#campaign-select').select2('val', '');
                            $('#channel-select').select2('val', '');
                            $('#source-select').select2('val', '');
                        }
                    });
            }
        });

        $("#url").on("change keyup paste mouseup", function() {
            if ($(this).data("last_result") != $("#url").val()) {
                $("#url-form-group .control-label").html('Link');
                $("#btn_shorten_url").text("Get tracked link").removeClass("btn_copy btn-success").addClass("btn_shorten btn-primary");
                $('#url-form-group').removeClass('has-error');
            }
        });

        var param = purl(window.location.href).param('u');
        if(param) {
            $("#url").val(param);
        }
    });
})();