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
                    placeholder: self.placeholder,
                    allowClear: true,
                    createSearchChoice:function(term, data) {
                        if(self.object_exists(term)) { return null; }

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
                return _.map(results, function(val) {
                    return {id: val.id, text: val.name}
                });
            });
        },
        object_exists: function(query) {
            return _.filter(this.objects, function(val) {
                return val.text.toLowerCase() == query.toLowerCase();
            }).length > 0;
        },
        on_change: function(e) {
            if(e.added && _.isString(e.added.id)) {
                this.create_object(e.added.id);
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

            this.$('.btn_shorten_url_clipboard').click(function() {
                self.toggle_copy_button();
            });
        },
        toggle_copy_button: function() {
            var self = this;

            this.clipboard_btn = this.$('.btn_shorten_url_clipboard');
            this.clipboard_btn.text("Copied").removeClass("btn-info").addClass("btn-success");

            setTimeout(function() {
                self.clipboard_btn.text("Copy").removeClass("btn-success").addClass("btn-info");
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
                    _.each(result.reverse(), function(link) {
                        self.add_link(link);
                    });

                    if(nb_links == 0) {
                        self.update_notification();
                    }
                })
                .fail(function() {
                    self.$el.append("<div class='alert alert-danger'>Unable to get recent links</div>");
                });            
        },
        add_link: function(link) {
            var nb_links = this.getChildren().length;

            var recent_link_box = new openerp.website_url.RecentLinkBox(this, link);
            recent_link_box.prependTo(this.$el);

            if(nb_links == 0) {
                this.update_notification();
            }
        },
        remove_links: function() {
            var links = this.getChildren();

            _.each(links, function(link) {
                link.remove();
            });
        },
        remove_link: function(link) {
            link.$el.remove();
            link.destroy();
        },
        update_notification: function() {
            if(this.getChildren().length == 0) {
                this.$el.find('.recent-links-notification').append("<div class='alert alert-info'>You don't have any recent links.</div>");
            }
            else {
                this.$el.find('.recent-links-notification').empty();
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

        // UTMS selects widgets
        var campaign_select = new openerp.website_url.SelectBox('campaigns');
        campaign_select.start($("#campaign-select"), 'e.g. Promotion of June, Winter Newsletter, ..');

        var medium_select = new openerp.website_url.SelectBox('mediums');
        medium_select.start($("#channel-select"), 'e.g. Newsletter, Social Network, ..');

        var source_select = new openerp.website_url.SelectBox('sources');
        source_select.start($("#source-select"), 'e.g. Search Engine, Website page, ..');

        // Recent Links Widgets
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

                // Get URL and UTMs
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
                            // Handle errors
                            if(result['error'] == 'empty_url')  {
                                $('.notification').html("<div class='alert alert-danger'>The URL is empty.</div>");
                            }
                            else if(result['error'] == 'url_not_found') {
                                $('.notification').html("<div class='alert alert-danger'>URL not found (404)</div>");
                            }
                            else {
                                $('.notification').html("<div class='alert alert-danger'>An error occur while trying to generate your link. Try again later.</div>");
                            }
                        }
                        else {
                            // Link generated, clean the form and show the link
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
                $('.notification').html('');
            }
        });

        // Paste the URL in param into the form
        var param = purl(window.location.href).param('u');
        if(param) {
            $("#url").val(param);
        }
    });
})();