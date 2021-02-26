#!/usr/bin/env node
"use strict";

const jayson = require("jayson");
const process = require("process");
const util = require("util");


async function main(scheme, domain, database, username, password) {
    //<a id=common>
    // Callback way
    const common = jayson.Client[scheme](`${scheme}://${domain}/RPC2`);
    common.request("version", [], (error, response) => {
        if (error) throw error;
        if (response.error) throw new Error(response.error.message);
        const version = response.result;
    });
    //</a>

    //<a id=models>
    // Promise way
    let response;
    const modelsClient = jayson.Client[scheme](`${scheme}://${username}:${password}@${domain}/RPC2?db=${database}`);
    const models = util.promisify(modelsClient.request).bind(modelsClient);

    response = await models("system.noop", []);
    if (response.error) throw new Error(response.error.message);
    //</a>
    console.log(response.result);

    //<a id=check_access_rights>
    response = await models("res.partner.check_access_rights", [{
        args: ["read"],
        kwargs: {
            raise_exception: false,
        },
    }]);
    if (response.error) throw new Error(response.error.message);
    const canAccess = response.result;
    //</a>
    console.log(canAccess);

    //<a id=list>
    response = await models("res.partner.search", [{
        kwargs: {
            domain: [["is_company", "=", false]],
        },
    }]);
    if (response.error) throw new Error(response.error.message);
    const recordIds1 = response.result;
    //</a>
    console.log(recordIds1);

    //<a id=pagination>
    response = await models("res.partner.search", [{
        kwargs: {
            domain: [["is_company", "=", false]],
            offset: 10,
            limit: 5,
        },
    }]);
    if (response.error) throw new Error(response.error.message);
    const recordIds2 = response.result;
    //</a>
    console.log(recordIds2)

    //<a id=count>
    response = await models("res.partner.search_count", [{
        kwargs: {
            domain: [["is_company", "=", false]],
        },
    }]);
    if (response.error) throw new Error(response.error.message);
    const count = response.result;
    //</a>
    console.log(count);

    //<a id=search_read>
    response = await models("res.partner.search_read", [{
        kwargs: {
            domain: [["is_company", "=", false]],
            fields: ["name", "title", "parent_name"],
            limit: 1,
        },
    }]);
    if (response.error) throw new Error(response.error.message);
    const recordData1 = response.result[0];
    //</a>
    console.log(recordData1);

    //<a id=read>
    response = await models("res.partner.read", [{
        records: recordIds1,
        kwargs: {
            fields: ["name", "title", "parent_name"],
        },
    }]);
    if (response.error) throw new Error(response.error.message);
    const recordData2 = response.result[0];
    //</a>
    console.log(recordData2);

    //<a id=fields_get>
    response = await models("res.bank.fields_get", [{
        kwargs: {
            attributes: ["type", "string"],
        },
    }]);
    if (response.error) throw new Error(response.error.message);
    const fields = response.result;
    //</a>
    console.log(fields);

    //<a id=create>
    response = await models("res.partner.create", [{
        args: [{name: "New Partner"}],
    }]);
    if (response.error) throw new Error(response.error.message);
    const newRecordIds = response.result;
    //</a>
    console.log(newRecordIds);

    //<a id=write>
    response = await models("res.partner.write", [{
        records: newRecordIds,
        args: [{name: "Newer partner"}],
    }]);
    if (response.error) throw new Error(response.error.message);

    // get record name after having changed it
    response = await models("res.partner.name_get", [{
        records: newRecordIds,
    }]);
    if (response.error) throw new Error(response.error.message);
    const recordsName = response.result;
    //</a>
    console.log(recordsName);

    //<a id=unlink>
    response = await models("res.partner.unlink", [{
        records: newRecordIds,
    }]);
    if (response.error) throw new Error(response.error.message);

    response = await models("res.partner.exists", [{
        records: newRecordIds,
    }]);
    if (response.error) throw new Error(response.error.message);
    const records = response.result;
    //</a>
    console.log(records);

    //<a id=ir.model>
    response = await models("ir.model.create", [{
        args: [{
            name: "Custom Model",
            model: "x_custom_model",
            state: "manual"
        }],
    }]);
    if (response.error) throw new Error(response.error.message);
    const xCustomModelId = response.result[0];

    // grant the admin CRUD operations
    response = await models("ir.model.data.check_object_reference", [{
        args: ["base", "group_system"],
    }]);
    if (response.error) throw new Error(response.error.message);
    const systemGroupId = response.result[1];

    response = models("ir.model.access.create", [{
        args: [{
            name: "access_x_custom_model_admin",
            model_id: xCustomModelId,
            group_id: systemGroupId,
            perm_read: true,
            perm_write: true,
            perm_create: true,
            perm_unlink: true,
        }],
    }]);
    if (response.error) throw new Error(response.error.message);

    // get the fields of our newly created model
    response = await models("x_custom_model.fields_get", [{
        kwargs: {
            attributes: ["type", "string"],
        },
    }]);
    if (response.error) throw new Error(response.error.message);
    const xCustomModelFields = response.result;
    //</a>
    console.log(xCustomModelFields);

    //<a id=ir.model.fields>
    // Add a new field "x_foo" on "x_custom_model"
    response = await models("ir.model.fields.create", [{
        args: [{
            model_id: xCustomModelId,  // from the above example
            name: "x_foo",
            ttype: "char",
            state: "manual",
        }],
    }]);
    if (response.error) throw new Error(response.error.message);

    // Create a new record and read it
    response = await models("x_custom_model.create", [{
        args: [{x_foo: "test record"}],
    }]);
    if (response.error) throw new Error(response.error.message);
    const xRecordIds = response.result;

    response = await models("x_custom_model.read", [{
        records: xRecordIds,
        kwargs: {
            fields: ["x_foo"],
        },
    }]);
    if (response.error) throw new Error(response.error.message);
    const xRecordData = response.result[0];
    //</a>
    console.log(xRecordData);
}

main(...process.argv.slice(2));
