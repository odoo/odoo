odoo.define('web_linkedin.web_linkedin', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var form_widgets = require('web.form_widgets');
var Model = require('web.Model');
var utils = require('web.utils');
var Widget = require('web.Widget');
var pyeval = require('web.pyeval');
var framework = require('web.framework');
var KanbanView = require('web_kanban.KanbanView');

/*---------------------------------------------------------
 * OpenERP web_linkedin (module)
 *---------------------------------------------------------*/

var QWeb = core.qweb;
var _t = core._t;

/*
* instance.web_linkedin.tester.test_authentication()
* Call check if the Linkedin session is open or open a connection popup
* return a deferrer :
*   - resolve if the authentication is true
*   - reject if the authentication is wrong or when the user logout
*/
var LinkedinTester = core.Class.extend({
    init: function() {
        this.is_set_keys = false;
    },
    test_linkedin: function (show_dialog) {
        var self = this;
        if (this.is_set_keys) {
            return $.when(this.is_key_set=true);
        }
        return new Model("linkedin").call("test_linkedin_keys", []).then(function(data) {
            if (data.is_key_set) {
                self.is_set_keys = data.is_key_set;
               return data;
             } else {
                if (show_dialog) {
                    self.show_error({'name': "Linkedin API key not set."});
                    return $.Deferred().reject();
                } else {
                    return data;
                }
            }
        });
    },
    show_error: function(error) {
        var self = this;
        var dialog = new instance.web.Dialog(self, {
            title: _t("LinkedIn is not enabled"),
            buttons: [
                {text: _t("Ok"), click: function() { dialog.$dialog_box.modal('hide'); }}
            ]
        }, QWeb.render('LinkedIn.DisabledWarning', {error: error})).open();
    }
});

var tester = new LinkedinTester();

var Linkedin = form_widgets.FieldChar.extend({
    init: function() {
        this._super.apply(this, arguments);
    },
    initialize_content: function() {
        var $ht = $(QWeb.render("FieldChar.linkedin"));
        var $in = this.$("input");
        $in.replaceWith($ht);
        this.$(".oe_linkedin_input").append($in);
        this.$(".oe_linkedin_img").click(_.bind(this.search_linkedin, this));
        this._super();
    },
    search_linkedin: function() {
        var self = this;
        if (!this.open_in_process) {
            this.open_in_process = true;
            tester.test_linkedin(true).done(function() {
                self.open_in_process = false;
                var text = (self.get("value") || "").replace(/^\s+|\s+$/g, "").replace(/\s+/g, " ");
                var pop = new LinkedinSearchPopup(self, text);
                pop.on("search_completed", self, function() {
                    pop.open();
                });
                pop.on("selected", this, function(entity) {
                    self.selected_entity(entity);
                });
                pop.do_search();
            });
        }
    },
    selected_entity: function(entity) {
        var self = this;
        this.create_on_change(entity).done(function(to_change) {
            var values = self.view.get_fields_values();
            _.each(to_change, function (value, key) {
                if (!/linkedin/.test(key) && !!values[key]) {
                    if(!_.isArray(values[key]) && values['id']) {
                        delete to_change[key];
                    }
                }
            });
            self.view.set_values(to_change);
        });
    },
    create_on_change: function(entity) {
        return entity.__type === "company" ? this.create_or_modify_company(entity) : this.create_or_modify_partner(entity);
    },
    create_or_modify_company: function (entity) {
        var self = this;
        var to_change = {};
        var image_def = null;
        to_change.is_company = true;
        to_change.name = entity.name;
        to_change.image = false;
        if (entity.logoUrl) {
            image_def = self.rpc('/web_linkedin/binary/url2binary',
                               {'url': entity.logoUrl}).then(function(data){
                to_change.image = data;
            });
        }
        to_change.website = entity.websiteUrl;
        to_change.phone = false;
        _.each((entity.locations || {}).values || [], function(el) {
            to_change.phone = el.contactInfo.phone1;
        });
        to_change.linkedin_url = _.str.sprintf("http://www.linkedin.com/company/%d", entity.id);

        _.each(to_change, function (val, key) {
            if (self.field_manager.datarecord[key]) {
                to_change[key] = self.field_manager.datarecord[key];
            }
        });

        to_change.child_ids = [];
        var children_def = $.Deferred();
        var context = pyeval.eval('context');
        //Here limit will be 25 because count range can between 0 to 25
       //https://developer.linkedin.com/documents/people-search-api
        res = new Model("linkedin").call("get_people_from_company", [entity.universalName, 25, window.location.href, context]).done(function(result) {
            if (result.people) {
                console.debug("Linkedin pepople in this company found :", result.numResults, "=>", result.people._count, result.people.values);
                var result = _.reject(result.people.values || [], function(el) {
                    return ! el.formattedName;
                });
                self.create_or_modify_company_partner(result).then(function (childs_to_change) {
                    _.each(childs_to_change, function (data) {
                        // [0,0,data] if it's a new partner
                        to_change.child_ids.push( data.id ? [1, data.id, data] : [0, 0, data] );
                    });
                    children_def.resolve();
                });
            } else { children_def.resolve(); /*No people found for the company, simply resolve child_def*/}
        }).fail(function () {
            children_def.reject();
        });

        return $.when(image_def, children_def).then(function () {
            return to_change;
        });
    },

    create_or_modify_company_partner: function (entities) {
        var self = this;
        var deferrer = $.Deferred();
        var defs = [];
        var childs_to_change = [];

        _.each(entities, function (entity, key) {
            var entity = _.extend(entity, {
                '__type': "people",
                '__company': entity.universalName,
                'parent_id': self.field_manager.datarecord.id || 0
            });
            defs.push(self.create_or_modify_partner_change(entity).then(function (to_change) {
                childs_to_change[key] = to_change;
            }));
        });
        $.when.apply($, defs).then(function () {
            new data.DataSetSearch(this, 'res.partner').call("linkedin_check_similar_partner", [entities]).then(function (partners) {
                _.each(partners, function (partner, i) {
                    _.extend(childs_to_change[i], partner);
                });
                deferrer.resolve(childs_to_change);
            });
        });
        return deferrer;
    },
    create_or_modify_partner: function (entity, rpc_search_similar_partner) {
        var self = this;
        return this.create_or_modify_partner_change(entity).then(function (to_change) {
            // find similar partners
            _.each(to_change, function (val, key) {
                if (self.field_manager.datarecord[key]) {
                    to_change[key] = self.field_manager.datarecord[key];
                }
            });
        return to_change;
        });
    },
    create_or_modify_partner_change: function (entity) {
        var to_change = {};
        var defs = [];
        to_change.is_company = false;
        to_change.name = entity.formattedName;
        if (entity.pictureUrl) {
            defs.push(this.rpc('/web_linkedin/binary/url2binary',
                               {'url': entity.pictureUrl}).then(function(data){
                to_change.image = data;
            }));
        }
        _.each((entity.phoneNumbers || {}).values || [], function(el) {
            if (el.phoneType === "mobile") {
                to_change.mobile = el.phoneNumber;
            } else {
                to_change.phone = el.phoneNumber;
            }
        });
        var positions = (entity.positions || {}).values || [];
        for (var key in positions) {
            var position = positions[key];
            if (position.isCurrent) {
                var company_name = position.company ? position.company.name : false;
                if (!entity.parent_id && entity.parent_id !== 0 && company_name) {
                    defs.push(new data.DataSetSearch(this, 'res.partner').call("search", [[["name", "=", company_name]]]).then(function (data) {
                        if(data[0]) to_change.parent_id = data[0];
                        else position.title = position.title + ' (' + company_name + ') ';
                        to_change.function = position.title;
                    }));
                } else if (!entity.__company || !company_name || company_name == entity.__company) {
                    to_change.function = position.title + (company_name ? ' (' + company_name + ') ':'');
                }
                break;
            }
        }

        if (entity.parent_id) {
            to_change.parent_id = entity.parent_id;
        }
        to_change.linkedin_url = entity.publicProfileUrl || false;
        to_change.linkedin_id = entity.id || false;

        return $.when.apply($, defs).then(function () {
            return to_change;
        });
    }
});
core.form_widget_registry.add('linkedin', Linkedin);

var Linkedin_url = form_widgets.FieldChar.extend({
    initialize_content: function() {
        this.$("input,span").replaceWith($(QWeb.render("FieldChar.linkedin_url")));
        this._super();
    },
    render_value: function() {
        this._super();
        this.$(".oe_linkedin_url").attr("href", this.field_manager.datarecord.linkedin_url || "#").toggle(!!this.field_manager.datarecord.linkedin_url);
    },
});
core.form_widget_registry.add('linkedin_url', Linkedin_url);


var commonPeopleFields = ["id", "picture-url", "public-profile-url", "first-name", "last-name",
                        "formatted-name", "location", "phone-numbers", "im-accounts",
                        "main-address", "headline", "positions", "summary", "specialties"];

var LinkedinSearchPopup = Dialog.extend({
    template: "Linkedin.popup",
    init: function(parent, search) {
        this._super(parent, { 'title': QWeb.render('LinkedIn.AdvancedSearch') });
        this.search = search;
        this.limit = 5;
        this.company_offset = 0;
        this.people_offset = 0;
    },
    start: function() {
        var self = this;
        this._super();
        this.bind_event();
        this.has_been_loaded = $.Deferred();
        $.when(this.has_been_loaded).done(function(profile) {
            self.display_account(profile);
        });
    },
    bind_event: function() {
        var self = this;
        this.$el.parents('.modal').on("click", ".oe_linkedin_logout", function () {
            self.rpc("/linkedin/linkedin_logout", {}).done(function(result) {
                if (result) {
                    self.destroy();
                }
            });
        });
        this.$search = this.$el.parents('.modal').find(".oe_linkedin_advanced_search" );
        this.$url = this.$search.find("input[name='search']" );
        this.$url.val(this.search);
        this.$span = this.$search.find("span");

        this.$span.on("click", function (e) {
            e.stopPropagation();
            self.search = '';
            self.do_search(self.$url.val() || '');
        });
        this.$url
            .on("click mousedown mouseup", function (e) {
                e.stopPropagation();
            }).on("keydown", function (e) {
                if(e.keyCode == 13) {
                    $(e.target).blur();
                    self.$span.click();
                }
            });
    },
    display_account: function(profile) {
        var self = this;
        $(QWeb.render('LinkedIn.loginInformation', profile)).appendTo(self.$el.parents('.modal').find(".oe_dialog_custom_buttons"));
    },
    do_search: function(url) {
        var self = this;
        var deferrers = [];
        var params = {};
        this.$(".oe_linkedin_pop_c .oe_linkedin_company_entities, .oe_linkedin_pop_c .oe_linkedin_show_more, .oe_linkedin_pop_p .oe_linkedin_people_entities, .oe_linkedin_pop_p .oe_linkedin_show_more").empty();
        this.company_offset = 0;
        this.people_offset = 0;

        if (url && url.length) {
            var url = url.replace(/\/+$/, ''); //Will remove trailing forward slace
            var uid = url.replace(/(.*linkedin\.com\/[a-z]+\/)|(^.*\/company\/)|(\&.*$)/gi, '');

            var re = /[^\w\d-_]/g //Will replace special characters except - and _
            if (re.test(uid)) { //Test whether url having special characters other than - and _
                uid = uid.replace(re, '');
            }
            _.extend(params, {'search_uid': uid});
            this.search = url;
        }
        var context = _.extend(pyeval.eval('context'), {'from_url': window.location.href});
        _.extend(params, {'search_term': this.search, 'from_url': window.location.href, 'local_context': context});
        self.rpc("/linkedin/get_search_popup_data", params).done(function(result) {
            if(result.status && result.status == 'need_auth') {
                framework.redirect(result.url);
            } else { //We can check (result.status == 'OK') and other status
                self.trigger('search_completed');
                self.has_been_loaded.resolve(result.current_profile);
                self.do_result_companies(result.companies);
                if (result.companies && result.companies.companies._total > (self.company_offset + self.limit)) {
                    var remaining = result.companies.companies._total - (self.company_offset + self.limit);
                    var $company_more = $(QWeb.render("Linkedin.show_more", {'remaining': remaining, class: 'company'}));
                    $company_more.on("click", self, function(e) {
                        self.do_more_companies(e, params);
                    });
                    self.$(".oe_linkedin_pop_c .oe_linkedin_show_more").html($company_more);
                }
                self.do_result_people(result.people);
                if (result.people && result.people.people._total > (self.people_offset + self.limit)) {
                    var remaining = result.people.people._total - (self.people_offset + self.limit);
                    var $people_more = $(QWeb.render("Linkedin.show_more", {'remaining': remaining, class: 'people'}));
                    $people_more.on("click", self, function(e) {
                        self.do_more_people(e, params);
                    });
                    self.$(".oe_linkedin_pop_p .oe_linkedin_show_more").html($people_more);
                }
                if (result.warnings) { self.show_warnings(result.warnings); }
                if (result.people_status == 403) {
                    $(".oe_linkedin_pop_p .oe_linkedin_people_entities").html($(QWeb.render("LinkedIn.PeopleAccess")));
                }
            }
        }).fail(function (error, event) {
            if (error.data.arguments[0] == 401) {
                var url = error.data.arguments[2].url || "";
                instance.web.redirect(url);
                //prevent crashmanager to diplay error
                event.preventDefault();
             }
        });
        return $.when.apply($, deferrers);
    },
    do_result_companies: function(companies) {
        var lst = (companies.companies || {}).values || [];
        lst = _.map(lst, function(el) {
            el.__type = "company";
            return el;
        });
        console.debug("Linkedin companies found:", (companies.companies || {})._total, '=>', lst.length, lst);
        return this.display_result(lst, this.$(".oe_linkedin_pop_c .oe_linkedin_company_entities"));
    },
    do_result_people: function(people) {
        var plst = (people.people || {}).values || [];
        plst = _.map(plst, function(el) {
            el.__type = "people";
            return el;
        });
        console.debug("Linkedin people found:", people.numResults, '=>', plst.length, plst);
        return this.display_result(plst, this.$(".oe_linkedin_pop_p"));
    },
    display_result: function(result, $elem) {
        var self = this;
        var $row;
        $elem.find(".oe_no_result").remove();
        _.each(result, function(el) {
            //To prevent creation of same entity twice, it is possible due to show more button or universal name which returns same entity twice
            if (self.$el.find(".linkedin_id_"+el.id).length) { return; }
            var pc = new EntityWidget(self, el);
            if (!$elem.find("div").size() || $elem.find(" > div:last > div").size() >= 5) {
                $row = $("<div style='display: table-row;width:100%'/>");
                $row.appendTo($elem);
            } else {
                $row = $elem.find(" > div:last");
            }
            pc.appendTo($row);
            pc.$el.css("display", "table-cell");
            pc.$el.css("width", "20%");
            pc.on("selected", self, function(data) {
                self.trigger("selected", data);
                self.destroy();
            });
        });
        if (!$(".oe_linkedin_pop_p").size()) {
            $elem.append($('<div class="oe_no_result">').text(_t("No results found")));
        }
    },
    do_more_people: function(event, params) {
        var self = this;
        new Model("linkedin").call("get_people_data", [this.people_offset += this.limit, this.limit, {}, {}], params).done(function(result) {
            self.do_result_people(result[1]);
            if (result[0] == 200 && result[1].people && (result[1].people._total - (self.people_offset+self.limit)) > 0) {
                self.$el.find(".oe_linkedin_show_more .people .oe_linkedin_remaining").text(result[1].people._total - (self.people_offset+self.limit));
            } else if (result[0] == 200) {
                self.$el.find(".oe_linkedin_show_more .people").remove();
            }
        });
    },
    do_more_companies: function(event, params) {
        var self = this;
        new Model("linkedin").call("get_company_data", [this.company_offset += this.limit, this.limit, {}, {}], params).done(function(result) {
            self.do_result_companies(result[1]);
            if (result[0] == 200 && result[1].companies && (result[1].companies._total - (self.company_offset+self.limit)) > 0) {
                self.$el.find(".oe_linkedin_show_more .company .oe_linkedin_remaining").text(result[1].companies._total - (self.company_offset+self.limit));
            } else if (result[0] == 200) {
                self.$el.find(".oe_linkedin_show_more .company").remove();
            }
       });
    },
    show_warnings: function(warnings) {
        var self = this;
        _.each(warnings, function(warning) {
            self.do_warn(warning[0], warning[1]);
        });
    }
});

var EntityWidget = Widget.extend({
    template: "Linkedin.EntityWidget",
    init: function(parent, data) {
        this._super(parent);
        this.data = data;
    },
    start: function() {
        var self = this;
        this.$el.click(function() {
            self.trigger("selected", self.data);
        });
        if (this.data.__type === "company") {
            this.$el.addClass("linkedin_id_"+this.data.id);
            this.$("h3").text(this.data.name);
            self.$("img").attr("src", this.data.logoUrl);
            self.$(".oe_linkedin_entity_headline").text(this.data.industry);
        } else { // people
            this.$el.addClass("linkedin_id_"+this.data.id);
            this.$("h3").text(this.data.formattedName);
            self.$("img").attr("src", this.data.pictureUrl);
            self.$(".oe_linkedin_entity_headline").text(this.data.headline);
        }
    },
});
    /*
    Kanban include for adding import button on button bar for res.partner model to import linkedin contacts
    */
    KanbanView.include({
        init: function() {
            this.display_dm = new utils.DropMisordered(true);
            return this._super.apply(this, arguments);
        },
        import_linkedin_contact: function() {
            var self = this;
            var super_res = this._super.apply(this, arguments);
            if(this.dataset.model == 'res.partner') {
                this.display_dm.add(tester.test_linkedin(false)).done(function() {
                    var $linkedin_button = $(QWeb.render("KanbanView.linkedinButton", {'widget': self}));
                    $linkedin_button.appendTo(self.$buttons);
                    $linkedin_button.click(function() {
                        var context = pyeval.eval('context');
                        var res = self.rpc("/linkedin/sync_linkedin_contacts", {
                            from_url: window.location.href,
                            local_context: context
                        }).done(function(result) {
                            if (result instanceof Object && result.status && result.status == 'need_auth') {
                                if (confirm(_t("You will be redirected to LinkedIn authentication page, once authenticated after that you use this widget."))) {
                                    framework.redirect(result.url);
                                }
                            }).fail(function (error, event) {
                                if (error.data.arguments[0] == 401) {
                                    var url = error.data.arguments[2].url || "";
                                    instance.web.redirect(url);
                                    //prevent crashmanager to diplay error
                                    event.preventDefault();
                                }
                            });
                        });
                    }
                });
        },
        load_kanban: function() {
            var self = this;
            var super_res = this._super.apply(this, arguments);
            if(this.dataset.model == 'res.partner' && !this.dataset.child_name) {
               self.import_linkedin_contact();
            }
            return super_res;
        }
    });
});
