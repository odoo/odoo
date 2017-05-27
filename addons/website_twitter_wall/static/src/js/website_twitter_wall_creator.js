odoo.define('website_twitter_wall.create', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var website = require('website.website');
var contentMenu = require('website.contentMenu');

var _t = core._t;

website.add_template_file('/website_twitter_wall/static/src/xml/website_twitter_wall_creator.xml');
contentMenu.EditorBarContent.include({
    create_twitter_wall: function() {
        (new Create(this)).appendTo($(document.body));
    },
});

var Create = Widget.extend({
    template: 'website_twitter_wall_create',
    events: {
        'click div.modal-footer > button': 'create',
        'change input.odoo-tw-create-image-upload': 'image_upload',
        'change input.odoo-tw-create-image-url': 'image_url',
        'click .list-group-item': function (ev) {
            this.$('.list-group-item').removeClass('active');
            this.$(ev.target).closest('li').addClass('active');
        }
    },
    start: function() {
        this.$el.modal();
        this.image = '';
        this.testRegex = /^https?:\/\/(?:[a-z\-]+\.)+[a-z]{2,6}(?:\/[^\/#?]+)+\.(?:jpe?g|gif|png)$/;
        this.set_tag_ids();
    },
    image_upload: function(e) {
        var self = this;
        this.clear_image_values('.odoo-tw-create-image-url');
        var fileName = e.target.files[0];
        var fr = new FileReader();
        fr.onload = function(ev) {
            self.$('.odoo-tw-create-image').attr('src', ev.target.result);
            self.image = ev.target.result.split(',')[1]
        }
        fr.readAsDataURL(fileName);
    },
    clear_image_values: function(el) {
        this.image = '';
        this.$('.form-group').removeClass('has-error');
        this.$(".error-dialog").remove();
        this.$(el).val("");
        this.$('.odoo-tw-create-image').attr('src','/website_twitter_wall/static/src/img/img_preview.png');
        this.$('.url-error').addClass("hidden");
    },
    image_url: function(e) {
        this.clear_image_values('.odoo-tw-create-image-upload');
        var url = e.target.value;
        if (this.testRegex.test(url)) {
            this.$('.odoo-tw-create-image').attr('src', url);
            this.image = url;
        } else {
            this.$('.url-error').removeClass("hidden");
        }
    },
    select2_wrapper: function (tag, multi, fetch_fnc) {
        return {
            width: '100%',
            placeholder: tag,
            allowClear: true,
            formatNoMatches: _.str.sprintf(_t("No matches found. Type to create new %s"), tag),
            multiple: multi,
            selection_data: false,
            fetch_rpc_fnc : fetch_fnc,
            formatSelection: function (data) {
                if (data.tag) {
                    data.text = data.tag;
                }
                return data.text;
            },
            createSearchChoice: function (term) {
                return {
                    id: _.uniqueId('tag_'),
                    create: true,
                    tag: term,
                    text: _.str.sprintf(_t("Create New %s '%s'"), tag, term)
                };
            },
            fill_data: function (query, data) {
                var self = this,
                    tags = {results: []};
                _.each(data, function (obj) {
                    if (self.matcher(query.term, obj.name)) {
                        tags.results.push({id: obj.id, text: obj.name });
                    }
                });
                query.callback(tags);
            },
            query: function (query) {
                var self = this;
                // Fetch data only once and store it
                if (!this.selection_data) {
                    this.fetch_rpc_fnc().then(function (data) {
                        self.fill_data(query, data);
                        self.selection_data = data;
                    });
                } else {
                    this.fill_data(query, this.selection_data);
                }
            },
        };
    },
    set_tag_ids: function () {
        this.$("input[name='tweetus_hashtag']").select2(this.select2_wrapper(_t('Hashtag'), true, function () {
            return ajax.jsonRpc("/web/dataset/call_kw", 'call', {
                model: 'twitter.hashtag',
                method: 'search_read',
                args: [],
                kwargs: {
                    fields: ['name'],
                    context: website.get_context()
                }
            });
        }));
    },
    get_tag_ids: function () {
        var res = [];
        _.each(this.$("input[name='tweetus_hashtag']").select2('data'),
            function (val) {
                if (val.create) {
                    res.push([0, 0, {'name': val.text}]);
                } else {
                    res.push([4, val.id]);
                }
            });
        return res;
    },
    create: function(e) {
        var self = this;
        this.$('.form-group').removeClass('has-error');
        this.$(".error-dialog").remove();
        this.$('.url-error').addClass("hidden");
        var wall_name = this.$(".odoo-tw-create-name").val().trim();
        var wall_description = this.$(".odoo-tw-create-description").val().trim();
        if(!this.image) {
            this.$('.odoo-tw-create-image-upload, .odoo-tw-create-image-url').closest('.form-group').addClass('has-error');
            return;
        }
        if(!wall_name) {
            this.$('.odoo-tw-create-name').closest('.form-group').addClass('has-error');
            return;
        }
        this.$('.odoo-tw-create-spinner').removeClass("hidden");
        ajax.jsonRpc("/twitter_wall/create", 'call', {
            'name': wall_name,
            'description': wall_description,
            'image': this.image,
            'is_url': this.testRegex.test(this.image),
            'website_published': this.$(e.target).data("published"),
            'tweetus_ids': this.get_tag_ids()
        }).then(function (data) {
            self.$('.odoo-tw-create-spinner').addClass("hidden");
            if(data.error){
                self.error(data.error)
            } else {
                self.$el.modal('hide');
                window.location = "/twitter_walls";
            }
        });
    },
    error: function (msg) {
        this.$(".odoo-tw-create-error").html(_.str.sprintf("<div class='error-dialog alert alert-danger'>%s</div>", _t(msg)));
    },
});
});