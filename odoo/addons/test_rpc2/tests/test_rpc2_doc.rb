#!/usr/bin/env ruby

require "uri"
require "xmlrpc/client"
XMLRPC::Config.const_set(:ENABLE_NIL_PARSER, true)

scheme = ARGV[0]
domain = ARGV[1]
database = ARGV[2]
username = ARGV[3]
password = ARGV[4]

#<a id=common>
common = XMLRPC::Client.new2("#{scheme}://#{domain}/RPC2")
version = common.call("version")
#</a>

#<a id=models>
models = XMLRPC::Client.new2(
    "#{scheme}://#{username}:#{password}@#{domain}/RPC2?db=#{database}")
models.call("system.noop")
#</a>

#<a id=check_access_rights>
partners = models.proxy("res.partner")
can_access = partners.check_access_rights({
    args: ["read"],
    kwargs: {
        raise_exception: false,
    },
})
#</a>

#<a id=list>
partners = models.proxy("res.partner")
record_ids = partners.search({
    kwargs: {
        domain: [["is_company", "=", false]],
    },
})
#</a>

#<a id=pagination>
partners = models.proxy("res.partner")
record_ids = partners.search({
    kwargs: {                        
        domain: [["is_company", "=", false]],
        offset: 10,
        limit: 5,
    }
})
#</a>

#<a id=count>
partners = models.proxy("res.partner")
count = partners.search_count({
    kwargs: {
        domain: [["is_company", "=", false]],
    }
})
#</a>

#<a id=search_read>
partners = models.proxy("res.partner")
record_data = partners.search_read({
    kwargs: {
        domain: [["is_company", "=", false]],
        fields: ["name", "title", "parent_name"],
        limit: 1,
    },
}).first
#</a>

#<a id=read>
partners = models.proxy("res.partner")
record_data = partners.read({
    records: record_ids,
    kwargs: {
        fields: ["name", "title", "parent_name"],
    },
}).first
#</a>

#<a id=fields_get>
banks = models.proxy("res.bank")
fields = banks.fields_get({
    kwargs: {
        attributes: %w(type, string),
    },
})
#</a>

#<a id=create>
partners = models.proxy("res.partner")
new_record_ids = partners.create({
    args: [{name: "New Partner"}]
})
#</a>

#<a id=write>
partners = models.proxy("res.partner")
partners.write({
    records: new_record_ids,
    args: [{name: "Newer partner"}]
})
# get record name after having changed it
records_name = partners.name_get({
    records: new_record_ids,
})
#</a>

#<a id=unlink>
partners = models.proxy("res.partner")
partners.unlink({
    records: new_record_ids,
})
# check if the deleted record is still in the database
records = partners.exists({
    records: new_record_ids,
})
#</a>

#<a id=ir.model>
x_custom_model_id = models.proxy("ir.model").create({
    args: [{
        name: "Custom Model",
        model: "x_custom_model",
        state: "manual",
    }],
}).first

# grant the admin CRUD operations
system_group_id = models.proxy("ir.model.data").check_object_reference({
    args: ["base", "group_system"]
})[1]
models.proxy("ir.model.access").create({
    args: [{
        name: "access_x_custom_model_admin",
        model_id: x_custom_model_id,
        group_id: system_group_id,
        perm_read: true,
        perm_write: true,
        perm_create: true,
        perm_unlink: true,
    }],
})

# get the fields of our newly created model
x_custom_model_fields = models.proxy("x_custom_model").fields_get({
    kwargs: {
        attributes: %w(type, string),
    }
})
#</a>

#<a id=ir.model.fields>
# Add a new field "x_foo" on "x_custom_model"
models.proxy("ir.model.fields").create({
    args: [{
        model_id: x_custom_model_id,  # from the above example
        name: "x_foo",
        ttype: "char",
        state: "manual",
    }],
})

# Create a new record and read it
x_record_ids = models.proxy("x_custom_model").create({
    args: [{x_foo: "test record"}]
}
)
x_record_data = models.proxy("x_custom_model").read({
    records: x_record_ids,
    kwargs: {
        fields: ["x_foo"],
    },
}).first
#</a>
