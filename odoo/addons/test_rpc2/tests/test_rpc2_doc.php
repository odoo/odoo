#!/usr/bin/env php

<?php

require "/tmp/vendor/autoload.php";

$scheme = $argv[1];
$domain = $argv[2];
$database = $argv[3];
$username = $argv[4];
$password = $argv[5];

//<a id=common>

$common = new Laminas\XmlRpc\Client("$scheme://$domain/RPC2");
$common->setSkipSystemLookup(true);
$version = $common->call("version");
//</a>

//<a id=models>
$modelsClient = new Laminas\XmlRpc\Client(
    "$scheme://$username:$password@$domain/RPC2?db=$database");
$modelsClient->setSkipSystemLookup(true);
$models = $modelsClient->getProxy();
$version = $models->system->noop();
//</a>

//<a id=check_access_rights>
$partners = $models->res->partner;
$can_access = $partners->check_access_rights([
    "args" => ["read"],
    "kwargs" => ["raise_exception" => false],
]);
//</a>

//<a id=list>
$partners = $models->res->partner;
$record_ids = $partners->search([
    "kwargs" => [
        "domain" => [["is_company", "=", false]],
    ],
]);
//</a>

//<a id=pagination>
$partners = $models->res->partner;
$partners->search([
    "kwargs" => [
        "domain" => [["is_company", "=", false]],
        "offset" => 10,
        "limit" => 5,
    ]
]);
//</a>

//<a id=count>
$partners = $models->res->partner;
$count = $partners->search_count([
    "kwargs" => [
        "domain" => [["is_company", "=", false]],
    ],
]);
//</a>

//<a id=search_read>
$partners = $models->res->partner;
$record_data = $partners->search_read([
    "kwargs" => [
        "domain" => [["is_company", "=", false]],
        "fields" => ["name", "title", "parent_name"],
        "limit" => 1,
    ],
])[0];
//</a>

//<a id=read>
$partners = $models->res->partner;
$record_data = $partners->read([
    "records" => $record_ids,
    "kwargs" => [
        "fields" => ["name", "title", "parent_name"],
    ],
])[0];
//</a>

//<a id=fields_get>
$banks = $models->res->bank;
$fields = $banks->fields_get([
    "kwargs" => [
        "attributes" => ["type", "string"],
    ],
]);
//</a>

//<a id=create>
$partners = $models->res->partner;
$new_record_ids = $partners->create([
    "args" => [["name" => "New Partner"]],
]);
//</a>

//<a id=write>
$partners = $models->res->partner;
$partners->write([
    "records" => $new_record_ids,
    "args" => [["name" => "Newer partner"]],
]);
// get record name after having changed it
$records_name = $partners->name_get([
    "records" => $new_record_ids,
]);
//</a>

//<a id=unlink>
$partners = $models->res->partner;
$partners->unlink([
    "records" => $new_record_ids,
]);
// check if the deleted record is still in the database
$records = $partners->exists([
    "records" => $new_record_ids,
]);
//</a>

//<a id=ir.model>
$x_custom_model_id = $models->ir->model->create([
    "args" => [[
        "name" => "Custom Model",
        "model" => "x_custom_model",
        "state" => "manual",
    ]],
])[0];

# grant the admin CRUD operations
$system_group_id = $models->ir->model->data->check_object_reference([
    "args" => ["base", "group_system"],
])[1];
$models->ir->model->access->create([
    "args" => [[
        "name" => "access_x_custom_model_admin",
        "model_id" => $x_custom_model_id,
        "group_id" => $system_group_id,
        "perm_read" => true,
        "perm_write" => true,
        "perm_create" => true,
        "perm_unlink" => true,
    ]],
]);

// get the fields of our newly created model
$x_custom_model_fields = $models->x_custom_model->fields_get([
    "kwargs" => [
        "attributes" => ["type", "string"],
    ],
]);

//<a id=ir.model.fields>
// Add a new field "x_foo" on "x_custom_model"
$models->ir->model->fields->create([
    "args" => [[
        "model_id" => $x_custom_model_id,  // above example
        "name" => "x_foo",
        "ttype" => "char",
        "state" => "manual",
    ]],
]);

// Create a new record and read it
$x_record_ids = $models->x_custom_model->create([
    "args" => [["x_foo" => "test record"]],
]);
$x_record_data = $models->x_custom_model->read([
    "records" => $x_record_ids,
    "kwargs" => [
        "fields" => ["x_foo"],
    ],
])[0];
//</a>
